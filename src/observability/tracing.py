import os
from dataclasses import dataclass

from litestar.plugins.opentelemetry import OpenTelemetryConfig
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


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


def configure_tracing(settings: TracingSettings) -> OpenTelemetryConfig | None:
    """Build the one process-wide ``TracerProvider`` and register it as the global
    default, so every span created anywhere in the process - this ASGI middleware's
    request spans, and any manual ``tracer.start_as_current_span(...)`` a handler adds
    later - lands in the same trace and ships to the same OTLP collector (Tempo). Returns
    ``None`` when tracing is disabled; the caller skips adding the middleware in that
    case.
    """
    if settings.otlp_endpoint is None:
        return None

    provider = TracerProvider(resource=Resource.create({SERVICE_NAME: settings.service_name}))
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.otlp_endpoint)))
    trace.set_tracer_provider(provider)

    return OpenTelemetryConfig(tracer_provider=provider)
