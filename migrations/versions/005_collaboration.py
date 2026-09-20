"""Create the collaboration domain schema."""

from migrations.sql import execute_snapshot

revision: str = "005_collaboration"
down_revision: str | None = "004_incidents"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    execute_snapshot(revision, "up")


def downgrade() -> None:
    execute_snapshot(revision, "down")
