"""Create the geo domain schema."""

from migrations.sql import execute_snapshot

revision: str = "002_geo"
down_revision: str | None = "001_identity"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    execute_snapshot(revision, "up")


def downgrade() -> None:
    execute_snapshot(revision, "down")
