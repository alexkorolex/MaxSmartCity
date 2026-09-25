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
    if settings.otlp_endpoint is None:
        return None

    provider = TracerProvider(resource=Resource.create({SERVICE_NAME: settings.service_name}))
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.otlp_endpoint)))
    trace.set_tracer_provider(provider)

    engine = db_config.get_engine()
    SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine, tracer_provider=provider)

    return OpenTelemetryConfig(tracer_provider=provider, exclude=_EXCLUDED_PATHS)
