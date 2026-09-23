"""Add a free-text city to identity.organization, for admin-panel city filtering."""

from migrations.sql import execute_snapshot

revision: str = "014_organization_city"
down_revision: str | None = "013_resident_house"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    execute_snapshot(revision, "up")


def downgrade() -> None:
    execute_snapshot(revision, "down")
