ALTER TABLE identity.organization DROP COLUMN in_reserve_registry;

-- statement-breakpoint

ALTER TABLE identity.organization DROP CONSTRAINT ck_organization_organization_registration_status;

-- statement-breakpoint

ALTER TABLE identity.organization DROP COLUMN registration_status;

-- statement-breakpoint

ALTER TABLE identity.organization DROP COLUMN license_number;

-- statement-breakpoint

ALTER TABLE identity.organization DROP COLUMN ogrn;

-- statement-breakpoint

ALTER TABLE identity.organization DROP COLUMN inn;

-- statement-breakpoint

ALTER TABLE identity.organization DROP CONSTRAINT ck_organization_organization_type;

-- statement-breakpoint

ALTER TABLE identity.organization ADD CONSTRAINT ck_organization_organization_type
    CHECK (type IN ('ADMINISTRATION', 'POWER_GRID', 'WATER_UTILITY', 'EMERGENCY'));

-- statement-breakpoint

ALTER TABLE identity.organization ALTER COLUMN type TYPE VARCHAR(14);
