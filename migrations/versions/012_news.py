"""Create the news domain schema."""

from migrations.sql import execute_snapshot

revision: str = "012_news"
down_revision: str | None = "011_notifications"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    execute_snapshot(revision, "up")


def downgrade() -> None:
    execute_snapshot(revision, "down")
