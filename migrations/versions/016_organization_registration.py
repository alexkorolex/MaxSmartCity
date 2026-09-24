"""Housing organizations (management companies / HOAs, Постановление №1616): new
organization types plus the INN/OGRN/license, moderation status and "Перечень"
(reserve registry) flag used by self-registration."""

from migrations.sql import execute_snapshot

revision: str = "016_organization_registration"
down_revision: str | None = "015_identity_role_seed"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    execute_snapshot(revision, "up")


def downgrade() -> None:
    execute_snapshot(revision, "down")
