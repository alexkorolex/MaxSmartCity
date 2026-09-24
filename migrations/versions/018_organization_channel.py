"""Per-organization notification channels (notifications.organization_channel) - where
an УК/ТСЖ receives residents' requests: MAX, e-mail or its own webhook."""

from migrations.sql import execute_snapshot

revision: str = "018_organization_channel"
down_revision: str | None = "017_house_management"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    execute_snapshot(revision, "up")


def downgrade() -> None:
    execute_snapshot(revision, "down")
