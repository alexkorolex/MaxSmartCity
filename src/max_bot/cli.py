import asyncio

import click
from litestar.plugins import CLIPlugin

from src.max_bot.certs import CertFetchError, fetch_russian_trusted_ca_certs
from src.max_bot.client import MaxClient
from src.max_bot.settings import MaxBotSettings

DEFAULT_UPDATE_TYPES = ("message_created", "message_callback", "bot_started", "bot_stopped")


@click.command(name="max-subscribe", help="Register this backend's webhook URL with MAX.")
def max_subscribe_command() -> None:
    settings = MaxBotSettings.from_environment()
    webhook_public_url = settings.webhook_public_url
    if not webhook_public_url:
        raise click.ClickException("MAX_WEBHOOK_PUBLIC_URL is required; see .env.example")

    async def _run() -> None:
        client = MaxClient(settings)
        result = await client.subscribe(
            url=webhook_public_url,
            update_types=list(DEFAULT_UPDATE_TYPES),
            secret=settings.webhook_secret,
        )
        click.echo(result)

    asyncio.run(_run())


@click.command(name="max-subscriptions", help="List active MAX webhook subscriptions.")
def max_subscriptions_command() -> None:
    settings = MaxBotSettings.from_environment()

    async def _run() -> None:
        client = MaxClient(settings)
        click.echo(await client.list_subscriptions())

    asyncio.run(_run())


@click.command(name="max-unsubscribe", help="Remove this backend's webhook URL from MAX.")
def max_unsubscribe_command() -> None:
    settings = MaxBotSettings.from_environment()
    webhook_public_url = settings.webhook_public_url
    if not webhook_public_url:
        raise click.ClickException("MAX_WEBHOOK_PUBLIC_URL is required; see .env.example")

    async def _run() -> None:
        client = MaxClient(settings)
        click.echo(await client.unsubscribe(url=webhook_public_url))

    asyncio.run(_run())


@click.command(
    name="max-fetch-certs",
    help="Download the Russian Trusted CA certs MAX's TLS chain needs into etc/max_api/certs/.",
)
def max_fetch_certs_command() -> None:
    try:
        fetched = fetch_russian_trusted_ca_certs()
    except (OSError, CertFetchError) as exc:
        raise click.ClickException(str(exc)) from exc
    for cert in fetched:
        click.echo(f"Wrote {cert.path}")
    click.echo(
        "Rebuild the backend image to pick up any changes (update-ca-certificates runs at build time)."
    )


class MaxBotCLIPlugin(CLIPlugin):
    def on_cli_init(self, cli: click.Group) -> None:
        cli.add_command(max_subscribe_command)
        cli.add_command(max_subscriptions_command)
        cli.add_command(max_unsubscribe_command)
        cli.add_command(max_fetch_certs_command)
