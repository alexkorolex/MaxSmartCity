from advanced_alchemy.extensions.litestar import SQLAlchemyInitPlugin
from litestar import Litestar, get
from litestar_autowire import AutowireConfig, AutowirePlugin
from litestar_granian import GranianPlugin

from src.database.config import DatabaseSettings


@get("/")
async def hello() -> dict[str, str]:
    return {"hello": "world"}


def create_app(database_url: str | None = None) -> Litestar:
    settings = DatabaseSettings(database_url) if database_url else DatabaseSettings.from_environment()
    return Litestar(
        route_handlers=[hello],
        plugins=[
            GranianPlugin(),
            SQLAlchemyInitPlugin(config=settings.plugin_config()),
            AutowirePlugin(AutowireConfig(domain_packages=["src.domains"])),
        ],
    )
