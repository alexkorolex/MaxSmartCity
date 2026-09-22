from litestar.logging import StructLoggingConfig
from litestar.middleware.logging import LoggingMiddlewareConfig
from litestar.plugins.structlog import StructlogConfig, StructlogPlugin

logging_config = StructLoggingConfig(pretty_print_tty=False)

middleware_logging_config = LoggingMiddlewareConfig(
    # Response bodies in particular can be huge (e.g. the ~85KB Swagger UI HTML the
    # Dockerfile's HEALTHCHECK hits every 30s) - logging them by default would flood
    # logs/memory with no real benefit; request/response metadata is still logged.
    request_log_fields=("path", "method", "content_type", "headers", "cookies", "query", "path_params"),
    response_log_fields=("status_code", "cookies", "headers"),
    # /schema (Swagger UI + OpenAPI JSON) is docs/healthcheck traffic, not application
    # activity - excluding it entirely keeps logs to things actually worth reading.
    exclude=["^/schema"],
)
structlog_plugin = StructlogPlugin(
    config=StructlogConfig(
        structlog_logging_config=logging_config, middleware_logging_config=middleware_logging_config
    )
)
