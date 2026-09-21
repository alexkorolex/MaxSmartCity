"""Add departments and Keycloak/LDAP identity linkage."""

from migrations.sql import execute_snapshot

revision: str = "008_identity_auth"
down_revision: str | None = "007_infrastructure"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    execute_snapshot(revision, "up")


def downgrade() -> None:
    execute_snapshot(revision, "down")
