"""Add the CLOSED report status: a resident's request is closed together with its
incident (confirmed by the resident, or auto-closed after the confirmation window)."""

from migrations.sql import execute_snapshot

revision: str = "019_report_closed_status"
down_revision: str | None = "018_organization_channel"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    execute_snapshot(revision, "up")


def downgrade() -> None:
    execute_snapshot(revision, "down")
