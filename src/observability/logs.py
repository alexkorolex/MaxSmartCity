from collections.abc import MutableMapping
from typing import Any

from litestar.logging import StructLoggingConfig
from litestar.logging.config import default_structlog_processors
from litestar.middleware.logging import LoggingMiddlewareConfig
from litestar.plugins.structlog import StructlogConfig, StructlogPlugin
from opentelemetry import trace


def _add_trace_context(
    _logger: object, _method_name: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    """Stamp every log line emitted inside an active span with its ``trace_id``/
    ``span_id`` - the join key that lets Grafana jump from a log line straight to the
    matching trace in Tempo (and back). A no-op outside of a request (no active span)."""
    span_context = trace.get_current_span().get_span_context()
    if span_context.is_valid:
        event_dict["trace_id"] = format(span_context.trace_id, "032x")
        event_dict["span_id"] = format(span_context.span_id, "016x")
    return event_dict


_processors = default_structlog_processors(as_json=True)
_processors.insert(-1, _add_trace_context)

logging_config = StructLoggingConfig(processors=_processors, pretty_print_tty=False)

middleware_logging_config = LoggingMiddlewareConfig(
    request_log_fields=("path", "method", "content_type", "headers", "cookies", "query", "path_params"),
    response_log_fields=("status_code", "cookies", "headers"),
    exclude=["^/schema"],
)
structlog_plugin = StructlogPlugin(
    config=StructlogConfig(
        structlog_logging_config=logging_config, middleware_logging_config=middleware_logging_config
    )
)
