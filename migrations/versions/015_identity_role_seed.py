"""Seed the three staff roles (admin/district_admin/housing_worker) into identity.role -
they have always been Keycloak realm roles but were never mirrored into this table,
even though identity.organization_member.role_id requires one."""

from migrations.sql import execute_snapshot

revision: str = "015_identity_role_seed"
down_revision: str | None = "014_merge_branches"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    execute_snapshot(revision, "up")


def downgrade() -> None:
    execute_snapshot(revision, "down")
