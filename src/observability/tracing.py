import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

from litestar.plugins.opentelemetry import OpenTelemetryConfig
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

if TYPE_CHECKING:
    from advanced_alchemy.config import SQLAlchemyAsyncConfig


_EXCLUDED_PATHS = ["^/metrics", "^/schema"]


@dataclass(frozen=True, slots=True)
class TracingSettings:
    """Optional, unlike the rest of this project's ``*Settings`` classes: leaving
    ``OTEL_EXPORTER_OTLP_ENDPOINT`` unset disables tracing entirely (``otlp_endpoint``
    comes back ``None``) rather than raising, so a plain dev/test run - or CI, which never
    has Tempo running - doesn't need to know about tracing at all."""

    otlp_endpoint: str | None
    service_name: str

    @classmethod
    def from_environment(cls) -> "TracingSettings":
        return cls(
            otlp_endpoint=os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT") or None,
            service_name=os.environ.get("OTEL_SERVICE_NAME", "maxsmartcity-backend"),
        )


def configure_tracing(
    settings: TracingSettings, db_config: "SQLAlchemyAsyncConfig"
) -> OpenTelemetryConfig | None:
    """Build the one process-wide ``TracerProvider`` and register it as the global
    default, so every span created anywhere in the process - this ASGI middleware's
    request spans, ``database_action``'s per-domain-operation spans (see
    ``src/database/logging.py``), and the SQLAlchemy instrumentation enabled below (one
    span per actual SQL statement, nested under whichever domain operation issued it) -
    lands in the same trace and ships to the same OTLP collector (Tempo). Returns
    ``None`` when tracing is disabled; the caller skips adding the middleware in that
    case, and SQLAlchemy is never instrumented, so a plain dev/test run pays nothing for
    any of this.

    ``db_config`` must be the exact same ``SQLAlchemyAsyncConfig`` instance later handed
    to ``SQLAlchemyInitPlugin`` - not a fresh copy. advanced_alchemy imports
    ``create_async_engine`` by name (``from sqlalchemy.ext.asyncio import
    create_async_engine``) at its own module load time, long before this function runs,
    so globally patching ``sqlalchemy.ext.asyncio.create_async_engine`` (the usual
    auto-instrumentation trick) never reaches the engine it actually creates. Calling
    ``db_config.get_engine()`` here creates the engine early and caches it on the config
    object (``engine_instance``); ``SQLAlchemyInitPlugin`` then reuses that same cached,
    already-instrumented instance instead of creating its own.
    """
    if settings.otlp_endpoint is None:
        return None

    provider = TracerProvider(resource=Resource.create({SERVICE_NAME: settings.service_name}))
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.otlp_endpoint)))
    trace.set_tracer_provider(provider)

    engine = db_config.get_engine()
    SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine, tracer_provider=provider)

    return OpenTelemetryConfig(tracer_provider=provider, exclude=_EXCLUDED_PATHS)
