import subprocess
import sys
from pathlib import Path

import click
from litestar.plugins import CLIPlugin

from src.max_bot.certs import CERT_URLS, CERTS_DIR, CertFetchError, fetch_russian_trusted_ca_certs

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"
ENV_EXAMPLE_FILE = PROJECT_ROOT / ".env.example"


def _env_keys(text: str) -> dict[str, str]:
    keys = {}
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key, _, value = stripped.partition("=")
            keys[key] = value
    return keys


def _sync_env_file() -> None:
    if not ENV_EXAMPLE_FILE.exists():
        return

    if not ENV_FILE.exists():
        ENV_FILE.write_text(ENV_EXAMPLE_FILE.read_text())
        click.echo(f"Created {ENV_FILE.name} from {ENV_EXAMPLE_FILE.name}")
        return

    existing_keys = _env_keys(ENV_FILE.read_text())
    missing_lines = [
        line
        for line in ENV_EXAMPLE_FILE.read_text().splitlines()
        if (stripped := line.strip())
        and not stripped.startswith("#")
        and "=" in stripped
        and stripped.partition("=")[0] not in existing_keys
    ]
    if not missing_lines:
        return

    with ENV_FILE.open("a") as handle:
        handle.write("\n" + "\n".join(missing_lines) + "\n")
    added = ", ".join(line.partition("=")[0] for line in missing_lines)
    click.echo(f"Added missing variables to {ENV_FILE.name}: {added}")


def _ensure_max_certs() -> None:
    """``etc/max_api/certs/`` is gitignored (regenerable, not vendored) - fetch it on a
    fresh clone so the backend image's ``COPY etc/max_api/certs/*.crt`` step doesn't fail."""
    if all((CERTS_DIR / name).exists() for name in CERT_URLS):
        return
    click.echo("Fetching MAX TLS trust anchors into etc/max_api/certs/ ...")
    try:
        fetch_russian_trusted_ca_certs()
    except (OSError, CertFetchError) as exc:
        raise click.ClickException(
            f"Could not fetch MAX TLS certs ({exc}). Run `litestar max-fetch-certs` manually "
            "once network access is available, then retry."
        ) from exc


@click.command(name="up", help="Sync .env from .env.example, then start the docker compose stack.")
@click.option("--build", is_flag=True, default=False, help="Rebuild images before starting.")
@click.option("--detach/--no-detach", default=True, help="Run containers in the background.")
def up_command(build: bool, detach: bool) -> None:
    _sync_env_file()
    _ensure_max_certs()

    command = ["docker", "compose", "up"]
    if detach:
        command.append("-d")
    if build:
        command.append("--build")

    result = subprocess.run(command, cwd=PROJECT_ROOT, check=False)
    sys.exit(result.returncode)


class OrchestrationCLIPlugin(CLIPlugin):
    def on_cli_init(self, cli: click.Group) -> None:
        cli.add_command(up_command)
