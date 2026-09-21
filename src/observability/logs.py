from litestar.logging import StructLoggingConfig
from litestar.plugins.structlog import StructlogConfig, StructlogPlugin

logging_config = StructLoggingConfig(pretty_print_tty=False)
structlog_plugin = StructlogPlugin(config=StructlogConfig(structlog_logging_config=logging_config))
