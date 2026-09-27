from pathlib import Path

from advanced_alchemy.extensions.litestar import SQLAlchemyInitPlugin
from dotenv import load_dotenv
from litestar import Litestar
from litestar.datastructures import State
from litestar.openapi.config import OpenAPIConfig
from litestar.openapi.plugins import SwaggerRenderPlugin
from litestar.plugins.prometheus import PrometheusController

from src.database.config import DatabaseSettings
from src.map.controllers import MapController
from src.observability.logs import logging_queue_lifespan, structlog_plugin
from src.observability.prometheus import prometheus_config
from src.security.keycloak import TOKEN_VERIFIER_STATE_KEY, KeycloakTokenVerifier

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env.local")
load_dotenv(PROJECT_ROOT / ".env", override=False)

MAP_DB_POOL_SIZE = 5


def create_map_app(database_url: str | None = None) -> Litestar:
    settings = DatabaseSettings(database_url) if database_url else DatabaseSettings.from_environment()
    return Litestar(
        route_handlers=[PrometheusController, MapController],
        state=State({TOKEN_VERIFIER_STATE_KEY: KeycloakTokenVerifier()}),
        plugins=[
            SQLAlchemyInitPlugin(config=settings.plugin_config(pool_size=MAP_DB_POOL_SIZE)),
            structlog_plugin,
        ],
        lifespan=[logging_queue_lifespan],
        middleware=[prometheus_config.middleware],
        openapi_config=OpenAPIConfig(
            title="Smart City Map",
            version="0.0.1",
            render_plugins=[SwaggerRenderPlugin(path="/schema")],
        ),
    )
