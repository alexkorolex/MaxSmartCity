"""Add optional MAX-bot account linkage for staff."""

from migrations.sql import execute_snapshot

revision: str = "009_operator_max_user_id"
down_revision: str | None = "008_identity_auth"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    execute_snapshot(revision, "up")


def downgrade() -> None:
    execute_snapshot(revision, "down")
