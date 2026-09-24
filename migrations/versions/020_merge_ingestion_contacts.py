"""Merge the ingestion-contacts branch (organization phones/e-mail/website from open
sources) with the housing-organizations branch (015 role seed .. 019 closed reports) -
both forked off 014_merge_branches independently."""

revision: str = "020_merge_ingestion_contacts"
down_revision: str | tuple[str, str] | None = ("015_ingestion_contacts", "019_report_closed_status")
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
