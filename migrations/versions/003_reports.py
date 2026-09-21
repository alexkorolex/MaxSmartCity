"""Create the reports domain schema."""

from migrations.sql import execute_snapshot

revision: str = "003_reports"
down_revision: str | None = "002_geo"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    execute_snapshot(revision, "up")


def downgrade() -> None:
    execute_snapshot(revision, "down")
