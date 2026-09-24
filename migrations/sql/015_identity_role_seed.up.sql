-- The three staff roles have always been Keycloak realm roles (see
-- keycloak/realm-export.json) but were never mirrored into identity.role, even though
-- identity.organization_member.role_id is NOT NULL and FKs into this table.
INSERT INTO identity.role (id, code, name)
VALUES
    ('e1000000-0000-4000-8000-000000000001', 'admin', 'Администратор'),
    ('e1000000-0000-4000-8000-000000000002', 'district_admin', 'Управа'),
    ('e1000000-0000-4000-8000-000000000003', 'housing_worker', 'Жилищник')
ON CONFLICT (code) DO NOTHING;
