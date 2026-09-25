"""Index normalized city/street/house number on geo.address - ingestion matches houses by
exact normalized address, which scanned the whole table once per imported house (bulk
GIS ЖКХ imports of tens of thousands of houses)."""

from migrations.sql import execute_snapshot

revision: str = "021_address_normalized_index"
down_revision: str | None = "020_merge_ingestion_contacts"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    execute_snapshot(revision, "up")


def downgrade() -> None:
    execute_snapshot(revision, "down")
