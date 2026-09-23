from pathlib import Path

from advanced_alchemy.extensions.litestar import SQLAlchemyInitPlugin
from dotenv import load_dotenv
from litestar import Litestar
from litestar.config.cors import CORSConfig
from litestar.config.response_cache import ResponseCacheConfig
from litestar.openapi.config import OpenAPIConfig
from litestar.openapi.plugins import SwaggerRenderPlugin
from litestar.plugins.prometheus import PrometheusController
from litestar_autowire import AutowireConfig, AutowirePlugin
from litestar_granian import GranianPlugin

from src.cli import OrchestrationCLIPlugin
from src.database.cache import CacheSettings
from src.database.config import DatabaseSettings
from src.max_bot.cli import MaxBotCLIPlugin
from src.max_bot.controllers import MaxWebhookController
from src.max_bot.startup import auto_subscribe_max_webhook
from src.observability.logs import structlog_plugin
from src.observability.prometheus import prometheus_config
from src.settings import CorsSettings

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env.local")
load_dotenv(PROJECT_ROOT / ".env", override=False)


def create_app(database_url: str | None = None, redis_url: str | None = None) -> Litestar:
    settings = DatabaseSettings(database_url) if database_url else DatabaseSettings.from_environment()
    cache_settings = CacheSettings(redis_url) if redis_url else CacheSettings.from_environment()
    cors_settings = CorsSettings.from_environment()
    return Litestar(
        route_handlers=[PrometheusController, MaxWebhookController],
        cors_config=CORSConfig(
            allow_origins=list(cors_settings.allowed_origins),
            allow_credentials=True,
            allow_headers=["*"],
            allow_methods=["*"],
        ),
        plugins=[
            GranianPlugin(),
            SQLAlchemyInitPlugin(config=settings.plugin_config()),
            AutowirePlugin(AutowireConfig(domain_packages=["src.domains"])),
            structlog_plugin,
            OrchestrationCLIPlugin(),
            MaxBotCLIPlugin(),
        ],
        stores={"response_cache": cache_settings.response_cache_store()},
        response_cache_config=ResponseCacheConfig(store="response_cache", default_expiration=300),
        on_startup=[auto_subscribe_max_webhook],
        openapi_config=OpenAPIConfig(
            title="Smart City Project",
            version="0.0.1",
            render_plugins=[
                SwaggerRenderPlugin(path="/schema"),
            ],
        ),
        middleware=[prometheus_config.middleware],
    )
