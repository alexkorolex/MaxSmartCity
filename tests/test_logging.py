"""The log format Grafana/Loki relies on: one JSON object per line, the traceback in its own
field, the trace id to jump to Tempo, and no secrets."""

import json
import logging
import queue
import sys
import time
from collections.abc import Iterator
from typing import Any

import pytest
from litestar import Litestar, get
from litestar.exceptions import NotFoundException
from litestar.testing import TestClient
from opentelemetry.sdk.trace import TracerProvider

from src.observability.logs import StructuredQueueHandler, logging_config, structlog_plugin

logger = logging.getLogger("src.tests.logging_probe")
tracer = TracerProvider().get_tracer(__name__)


@get("/unhandled")
async def unhandled() -> None:
    raise RuntimeError("the database is gone")


@get("/missing")
async def missing() -> None:
    raise NotFoundException("Report was not found")


@pytest.fixture
def client(capfd: pytest.CaptureFixture[str]) -> Iterator[TestClient]:
    # ``capfd`` first: the loggers bind to whatever stdout/stderr is when the app starts.
    with TestClient(Litestar([unhandled, missing], plugins=[structlog_plugin])) as test_client:
        yield test_client


def _entries(capfd: pytest.CaptureFixture[str], *, until: str) -> list[dict[str, Any]]:
    """Standard-library records are written by a background listener thread - wait for them."""
    lines: list[str] = []
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        captured = capfd.readouterr()
        lines += (captured.out + captured.err).splitlines()
        if any(until in line for line in lines):
            break
        time.sleep(0.02)
    return [json.loads(line) for line in lines if line.startswith("{")]


def _render(record: logging.LogRecord) -> dict[str, Any]:
    """What the app does with a standard-library record, minus the thread in between:
    ``prepare`` in the caller's context, then the configured JSON formatter."""
    standard_lib_config = logging_config.standard_lib_logging_config
    assert standard_lib_config is not None
    formatter_config = dict(standard_lib_config.formatters["standard"])
    formatter = formatter_config.pop("()")(**formatter_config)
    prepared = StructuredQueueHandler(queue.Queue()).prepare(record)
    return json.loads(formatter.format(prepared))


def test_a_logged_exception_is_one_json_entry_with_its_traceback_and_trace_id() -> None:
    with tracer.start_as_current_span("request") as span:
        try:
            raise ConnectionError("SMTP server refused the connection")
        except ConnectionError:
            record = logger.makeRecord(
                logger.name,
                logging.ERROR,
                __file__,
                0,
                "Could not send the e-mail to %s",
                ("staff@uk.ru",),
                sys.exc_info(),
                extra={"report_id": "r-1"},
            )
        entry = _render(record)

    assert entry["event"] == "Could not send the e-mail to staff@uk.ru"
    assert entry["level"] == "error"
    assert entry["logger"] == "src.tests.logging_probe"
    assert entry["report_id"] == "r-1"
    assert entry["exc_type"] == "builtins.ConnectionError"
    assert entry["exc_message"] == "SMTP server refused the connection"
    assert entry["exception"].startswith("Traceback (most recent call last):")
    assert entry["trace_id"] == format(span.get_span_context().trace_id, "032x")
    assert "message" not in entry


def test_an_unhandled_server_error_is_logged_but_a_client_error_is_not(
    client: TestClient, capfd: pytest.CaptureFixture[str]
) -> None:
    assert client.get("/missing").status_code == 404
    assert client.get("/unhandled").status_code == 500

    errors = [e for e in _entries(capfd, until="Unhandled exception") if e.get("level") == "error"]
    [entry] = errors
    assert entry["event"] == "Unhandled exception while serving a request"
    assert entry["path"] == "/unhandled"
    assert entry["method"] == "GET"
    assert entry["exc_type"] == "builtins.RuntimeError"
    assert "the database is gone" in entry["exception"]


def test_secret_headers_never_reach_the_request_log(
    client: TestClient, capfd: pytest.CaptureFixture[str]
) -> None:
    secrets = {
        "Authorization": "Bearer tok-7f3a9c",
        "X-Bot-Secret": "val-b0t-51c2",
        "X-Max-Bot-Api-Secret": "val-m4x-88e0",
        "X-Bootstrap-Secret": "val-b00t-3d17",
    }
    client.get("/missing", headers=secrets)

    output = json.dumps(_entries(capfd, until="HTTP Request"))
    assert "HTTP Request" in output
    for value in secrets.values():
        assert value not in output
