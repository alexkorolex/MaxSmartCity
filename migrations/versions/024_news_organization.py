"""News belongs to the organization that published it (news.news_post.organization_id) - it
reaches only the residents of the houses that organization manages."""

from migrations.sql import execute_snapshot

revision: str = "024_news_organization"
down_revision: str | None = "023_resident_max_chat"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    execute_snapshot(revision, "up")


def downgrade() -> None:
    execute_snapshot(revision, "down")
