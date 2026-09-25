"""The resident's dialog with the bot (identity.resident.max_chat_id) and the push marker
of in-app notifications duplicated to MAX (notifications.notification.pushed_at)."""

from migrations.sql import execute_snapshot

revision: str = "023_resident_max_chat"
down_revision: str | None = "022_report_chat"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    execute_snapshot(revision, "up")


def downgrade() -> None:
    execute_snapshot(revision, "down")
