"""Standing "organization manages house" relationship (geo.house_management) - which
УК/ТСЖ receives residents' requests for a given house."""

from migrations.sql import execute_snapshot

revision: str = "017_house_management"
down_revision: str | None = "016_organization_registration"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    execute_snapshot(revision, "up")


def downgrade() -> None:
    execute_snapshot(revision, "down")
