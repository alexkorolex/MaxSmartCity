"""Add incident grouping audit and concurrency indexes."""

from migrations.sql import execute_snapshot

revision: str = "011_incident_core"
down_revision: str | None = "010_ingestion"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    execute_snapshot(revision, "up")


def downgrade() -> None:
    execute_snapshot(revision, "down")
