"""Chat between a resident and the organization working on their report
(reports.report_message), plus the CHAT_MESSAGE in-app notification type."""

from migrations.sql import execute_snapshot

revision: str = "022_report_chat"
down_revision: str | None = "021_address_normalized_index"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    execute_snapshot(revision, "up")


def downgrade() -> None:
    execute_snapshot(revision, "down")
