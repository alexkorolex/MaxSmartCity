"""Create the infrastructure domain schema."""

from migrations.sql import execute_snapshot

revision: str = "007_infrastructure"
down_revision: str | None = "006_audit"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    execute_snapshot(revision, "up")


def downgrade() -> None:
    execute_snapshot(revision, "down")
