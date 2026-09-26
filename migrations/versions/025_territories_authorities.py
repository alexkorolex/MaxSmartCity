from migrations.sql import execute_snapshot

revision: str = "025_territories_authorities"
down_revision: str | None = "024_news_organization"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    execute_snapshot(revision, "up")


def downgrade() -> None:
    execute_snapshot(revision, "down")
