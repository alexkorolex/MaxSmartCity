"""Add provenance and reference organizations for file ingestion."""

from migrations.sql import execute_snapshot

revision: str = "010_ingestion"
down_revision: str | None = "009_operator_max_user_id"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    execute_snapshot(revision, "up")


def downgrade() -> None:
    execute_snapshot(revision, "down")
