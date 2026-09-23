from litestar.logging import StructLoggingConfig
from litestar.middleware.logging import LoggingMiddlewareConfig
from litestar.plugins.structlog import StructlogConfig, StructlogPlugin

logging_config = StructLoggingConfig(pretty_print_tty=False)

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
