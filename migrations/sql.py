from pathlib import Path

from alembic import op


def execute_snapshot(revision: str, direction: str) -> None:
    path = Path(__file__).parent / "sql" / f"{revision}.{direction}.sql"
    for statement in path.read_text(encoding="utf-8").split("-- statement-breakpoint"):
        if statement.strip():
            op.execute(statement.strip())
