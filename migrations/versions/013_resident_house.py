"""Add a resident's own selected home, editable any time from their profile."""

from migrations.sql import execute_snapshot

revision: str = "013_resident_house"
down_revision: str | None = "012_news"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    execute_snapshot(revision, "up")


def downgrade() -> None:
    execute_snapshot(revision, "down")
