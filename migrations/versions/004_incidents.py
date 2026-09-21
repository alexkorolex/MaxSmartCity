"""Create the incidents domain schema."""

from migrations.sql import execute_snapshot

revision: str = "004_incidents"
down_revision: str | None = "003_reports"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    execute_snapshot(revision, "up")


def downgrade() -> None:
    execute_snapshot(revision, "down")
