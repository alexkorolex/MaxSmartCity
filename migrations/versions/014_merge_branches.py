"""Merge the notifications/news branch (since extended with the resident's own house and
the organization city filter) and the incident-core/gis-zkh branch, which both forked off
010_ingestion independently."""

revision: str = "014_merge_branches"
down_revision: str | tuple[str, str] | None = ("014_organization_city", "013_incident_mvp")
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
