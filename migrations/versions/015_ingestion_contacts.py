from migrations.sql import execute_snapshot

revision: str = "015_ingestion_contacts"
down_revision: str | None = "014_merge_branches"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    execute_snapshot(revision, "up")


def downgrade() -> None:
    execute_snapshot(revision, "down")
