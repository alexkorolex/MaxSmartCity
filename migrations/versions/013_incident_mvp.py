"""Seed the resident problem catalog and protect active assignments."""

from migrations.sql import execute_snapshot

revision: str = "013_incident_mvp"
down_revision: str | None = "012_incident_core"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    execute_snapshot(revision, "up")


def downgrade() -> None:
    execute_snapshot(revision, "down")
