import subprocess
import sys
from pathlib import Path

import click
from litestar.plugins import CLIPlugin

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


@click.command(name="up", help="Sync .env from .env.example, then start the docker compose stack.")
@click.option("--build", is_flag=True, default=False, help="Rebuild images before starting.")
@click.option("--detach/--no-detach", default=True, help="Run containers in the background.")
def up_command(build: bool, detach: bool) -> None:
    _sync_env_file()

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
