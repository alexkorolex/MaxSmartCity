"""Structured logs: every line on stdout is one JSON object, so promtail ships it to Loki as
a single entry - a traceback stays with its message instead of becoming one entry per line.

Fields of an entry:

- ``event`` - the message itself, without the traceback;
- ``level``, ``logger``, ``timestamp``;
- ``trace_id``/``span_id`` - open the request's trace in Tempo right from the log line;
- the ``extra={...}`` context the call site passed;
- for errors, ``exc_type`` and ``exc_message`` (filter and group by them) plus the full
  ``exception`` traceback, chained causes (``raise ... from exc``) included.

The same chain renders both our code's standard ``logging`` records and Litestar's own
structlog entries (request/response log, unhandled exceptions).
"""

import copy
import logging
import logging.handlers
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from litestar import Litestar
from litestar.exceptions import HTTPException
from litestar.logging import StructLoggingConfig
from litestar.logging.config import LoggingConfig, default_json_serializer, stdlib_json_serializer
from litestar.logging.standard import LoggingQueueListener
from litestar.middleware.logging import LoggingMiddlewareConfig
from litestar.plugins.structlog import StructlogConfig, StructlogPlugin
from litestar.status_codes import HTTP_500_INTERNAL_SERVER_ERROR
from litestar.types import Logger, Scope
from opentelemetry import trace
from structlog.typing import EventDict, Processor, WrappedLogger

# Header values that must never reach the logs - bearer tokens and shared secrets.
_SECRET_HEADERS = frozenset(
    {"Authorization", "Cookie", "X-API-KEY", "X-Bot-Secret", "X-Bootstrap-Secret", "X-Max-Bot-Api-Secret"}
)
# ``logging.Formatter`` leftovers ``ExtraAdder`` would otherwise copy into every entry.
_NOISE_KEYS = ("message", "color_message")


def _add_trace_context(_logger: WrappedLogger, _method_name: str, event_dict: EventDict) -> EventDict:
    span_context = trace.get_current_span().get_span_context()
    if span_context.is_valid:
        event_dict["trace_id"] = format(span_context.trace_id, "032x")
        event_dict["span_id"] = format(span_context.span_id, "016x")
    return event_dict


def _add_logger_name(logger: WrappedLogger, _method_name: str, event_dict: EventDict) -> EventDict:
    record = event_dict.get("_record")
    name = record.name if record is not None else getattr(logger, "name", None)
    if name:
        event_dict.setdefault("logger", name)
    return event_dict


def _add_exception_fields(_logger: WrappedLogger, _method_name: str, event_dict: EventDict) -> EventDict:
    """``exc_type``/``exc_message`` next to the traceback - ``format_exc_info`` (which runs
    after this) turns ``exc_info`` into the ``exception`` text."""
    exc_info = event_dict.get("exc_info")
    if exc_info is True:
        exc_info = sys.exc_info()
    exception = exc_info if isinstance(exc_info, BaseException) else None
    if isinstance(exc_info, tuple):
        exception = exc_info[1]
    if exception is not None:
        event_dict["exc_type"] = f"{type(exception).__module__}.{type(exception).__qualname__}"
        event_dict["exc_message"] = str(exception)
    return event_dict


def _drop_noise(_logger: WrappedLogger, _method_name: str, event_dict: EventDict) -> EventDict:
    for key in _NOISE_KEYS:
        event_dict.pop(key, None)
    return event_dict


_RECORD_PROCESSORS: list[Processor] = [
    structlog.processors.add_log_level,
    _add_logger_name,
    structlog.processors.TimeStamper(fmt="iso", utc=True),
    _add_exception_fields,
    structlog.processors.format_exc_info,
]
# Litestar's own structlog entries are rendered in the calling context - take it directly.
_SHARED_PROCESSORS: list[Processor] = [
    structlog.contextvars.merge_contextvars,
    _add_trace_context,
    *_RECORD_PROCESSORS,
]


class StructuredQueueHandler(logging.handlers.QueueHandler):
    """Hands records to the background listener thread, which formats and writes them.

    ``prepare`` runs in the logging call's own thread and context, so this is where the
    request's trace id and structlog context variables are captured - on the listener
    thread they are gone. It also keeps ``exc_info``: the stock ``prepare`` renders the
    traceback into the message text and drops it, so it could not get its own field."""

    def prepare(self, record: logging.LogRecord) -> logging.LogRecord:
        record = copy.copy(record)
        record.msg = record.getMessage()
        record.args = None
        context: EventDict = dict(structlog.contextvars.get_contextvars())
        _add_trace_context(None, "", context)
        for key, value in context.items():
            record.__dict__.setdefault(key, value)
        return record


class StructuredLoggingQueueListener(LoggingQueueListener):
    """Make listener shutdown safe for both application teardown and Python ``atexit``."""

    def stop(self) -> None:
        if getattr(self, "_thread", None) is not None:
            super().stop()


@asynccontextmanager
async def logging_queue_lifespan(_app: Litestar) -> AsyncIterator[None]:
    """Drain and stop active logging queues before their output streams are closed."""

    try:
        yield
    finally:
        stop_logging_queue_listeners()


def stop_logging_queue_listeners() -> None:
    """Synchronously drain every structured queue listener exactly once."""

    for handler in logging.getLogger().handlers:
        if isinstance(handler, StructuredQueueHandler):
            listener = getattr(handler, "listener", None)
            if isinstance(listener, StructuredLoggingQueueListener):
                listener.stop()


def _standard_lib_logging_config() -> LoggingConfig:
    """Our code logs through ``logging.getLogger(__name__)`` - render those records with the
    very same processors as structlog's own entries."""
    return LoggingConfig(
        formatters={
            "standard": {
                "()": structlog.stdlib.ProcessorFormatter,
                # Context and trace ids were captured by ``StructuredQueueHandler.prepare`` and
                # arrive as record attributes, which ``ExtraAdder`` copies like any ``extra``.
                "foreign_pre_chain": [structlog.stdlib.ExtraAdder(), *_RECORD_PROCESSORS, _drop_noise],
                "processors": [
                    structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                    structlog.processors.JSONRenderer(serializer=stdlib_json_serializer),
                ],
            }
        },
        handlers={
            "console": {"class": "logging.StreamHandler", "level": "DEBUG", "formatter": "standard"},
            # Writing to stdout happens on a listener thread, never blocking the event loop.
            "queue_listener": {
                "class": f"{__name__}.StructuredQueueHandler",
                "level": "DEBUG",
                "queue": {"()": "queue.Queue", "maxsize": -1},
                "listener": f"{__name__}.StructuredLoggingQueueListener",
                "handlers": ["console"],
            },
        },
    )


def _log_unhandled_exception(logger: Logger, scope: Scope, _traceback: list[str]) -> None:
    """Called by Litestar inside the ``except`` block of a failed request. 4xx ``HTTPException``s
    are the client's mistake, already visible in the access log with their status code - only
    real server errors are logged, each with its full traceback."""
    exception = sys.exc_info()[1]
    status_code = getattr(exception, "status_code", HTTP_500_INTERNAL_SERVER_ERROR)
    if isinstance(exception, HTTPException) and status_code < HTTP_500_INTERNAL_SERVER_ERROR:
        return
    logger.exception(
        "Unhandled exception while serving a request",
        method=scope.get("method"),
        path=scope.get("path"),
        connection_type=scope.get("type"),
        status_code=status_code,
    )


logging_config = StructLoggingConfig(
    # Litestar's structlog logger writes bytes, the standard library handler writes text.
    processors=[*_SHARED_PROCESSORS, structlog.processors.JSONRenderer(serializer=default_json_serializer)],
    standard_lib_logging_config=_standard_lib_logging_config(),
    pretty_print_tty=False,
    log_exceptions="always",
    exception_logging_handler=_log_unhandled_exception,
)

middleware_logging_config = LoggingMiddlewareConfig(
    request_log_fields=("path", "method", "content_type", "headers", "cookies", "query", "path_params"),
    response_log_fields=("status_code", "cookies", "headers"),
    request_headers_to_obfuscate=set(_SECRET_HEADERS),
    response_headers_to_obfuscate={"Set-Cookie"},
    exclude=["^/schema", "^/metrics"],
)
structlog_plugin = StructlogPlugin(
    config=StructlogConfig(
        structlog_logging_config=logging_config, middleware_logging_config=middleware_logging_config
    )
)
