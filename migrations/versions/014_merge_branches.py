"""Merge the notifications/news branch and the incident-core/gis-zkh branch, which both
forked off 010_ingestion independently."""

revision: str = "014_merge_branches"
down_revision: str | tuple[str, str] | None = ("012_news", "013_incident_mvp")
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
