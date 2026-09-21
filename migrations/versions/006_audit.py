"""Create the audit domain schema."""

from migrations.sql import execute_snapshot

revision: str = "006_audit"
down_revision: str | None = "005_collaboration"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    execute_snapshot(revision, "up")


def downgrade() -> None:
    execute_snapshot(revision, "down")
