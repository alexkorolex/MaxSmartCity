-- Widen first: the new enum values are longer than the column's current auto-sized width.
ALTER TABLE identity.organization ALTER COLUMN type TYPE VARCHAR(32);

-- statement-breakpoint

ALTER TABLE identity.organization DROP CONSTRAINT ck_organization_organization_type;

-- statement-breakpoint

ALTER TABLE identity.organization ADD CONSTRAINT ck_organization_organization_type
    CHECK (type IN ('ADMINISTRATION', 'POWER_GRID', 'WATER_UTILITY', 'EMERGENCY', 'MANAGEMENT_COMPANY', 'HOA'));

-- statement-breakpoint

ALTER TABLE identity.organization ADD COLUMN inn VARCHAR(12);

-- statement-breakpoint

ALTER TABLE identity.organization ADD COLUMN ogrn VARCHAR(15);

-- statement-breakpoint

ALTER TABLE identity.organization ADD COLUMN license_number VARCHAR(255);

-- statement-breakpoint

ALTER TABLE identity.organization ADD COLUMN registration_status VARCHAR(8) DEFAULT 'APPROVED' NOT NULL;

-- statement-breakpoint

ALTER TABLE identity.organization ADD CONSTRAINT ck_organization_organization_registration_status
    CHECK (registration_status IN ('PENDING', 'APPROVED', 'REJECTED'));

-- statement-breakpoint

ALTER TABLE identity.organization ADD COLUMN in_reserve_registry BOOLEAN DEFAULT false NOT NULL;
