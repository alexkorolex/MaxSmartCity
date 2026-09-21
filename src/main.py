from pathlib import Path

from advanced_alchemy.extensions.litestar import SQLAlchemyInitPlugin
from dotenv import load_dotenv
from litestar import Litestar
from litestar.config.response_cache import ResponseCacheConfig
from litestar.openapi.config import OpenAPIConfig
from litestar.openapi.plugins import SwaggerRenderPlugin
from litestar.plugins.prometheus import PrometheusController
from litestar_autowire import AutowireConfig, AutowirePlugin
from litestar_granian import GranianPlugin

from src.cli import OrchestrationCLIPlugin
from src.database.cache import CacheSettings
from src.database.config import DatabaseSettings
from src.observability.logs import structlog_plugin
from src.observability.prometheus import prometheus_config

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def create_app(database_url: str | None = None, redis_url: str | None = None) -> Litestar:
    settings = DatabaseSettings(database_url) if database_url else DatabaseSettings.from_environment()
    cache_settings = CacheSettings(redis_url) if redis_url else CacheSettings.from_environment()
    return Litestar(
        route_handlers=[PrometheusController],
        plugins=[
            GranianPlugin(),
            SQLAlchemyInitPlugin(config=settings.plugin_config()),
            AutowirePlugin(AutowireConfig(domain_packages=["src.domains"])),
            structlog_plugin,
            OrchestrationCLIPlugin(),
        ],
        stores={"response_cache": cache_settings.response_cache_store()},
        response_cache_config=ResponseCacheConfig(store="response_cache", default_expiration=300),
        openapi_config=OpenAPIConfig(
            title="Max Smart City Project",
            version="0.0.1",
            render_plugins=[
                SwaggerRenderPlugin(path="/schema"),
            ],
        ),
        middleware=[prometheus_config.middleware],
    )


app = create_app()
