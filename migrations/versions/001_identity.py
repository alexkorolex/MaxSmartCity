"""Create the identity domain schema."""

from migrations.sql import execute_snapshot

revision: str = "001_identity"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    execute_snapshot(revision, "up")


def downgrade() -> None:
    execute_snapshot(revision, "down")
