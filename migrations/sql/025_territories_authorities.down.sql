DROP TABLE correspondence.message;

-- statement-breakpoint

DROP TABLE correspondence.conversation;

-- statement-breakpoint

DROP SCHEMA correspondence;

-- statement-breakpoint

ALTER TABLE identity.organization DROP CONSTRAINT ck_organization_authority_has_territory;

-- statement-breakpoint

ALTER TABLE identity.organization DROP COLUMN territory_id;

-- statement-breakpoint

ALTER TABLE identity.organization DROP COLUMN authority_kind;

-- statement-breakpoint

DROP INDEX geo.uq_administrative_area_parent_name;

-- statement-breakpoint

ALTER TABLE geo.administrative_area DROP CONSTRAINT ck_administrative_area_root_is_city;

-- statement-breakpoint

ALTER TABLE geo.administrative_area DROP CONSTRAINT ck_administrative_area_administrative_area_type;

-- statement-breakpoint

UPDATE geo.house SET administrative_area_id = NULL WHERE administrative_area_id IS NOT NULL;

-- statement-breakpoint

DELETE FROM geo.administrative_area WHERE geometry IS NULL OR type NOT IN ('CITY', 'DISTRICT', 'OTHER');

-- statement-breakpoint

ALTER TABLE geo.administrative_area ALTER COLUMN type TYPE VARCHAR(8);

-- statement-breakpoint

ALTER TABLE geo.administrative_area ADD CONSTRAINT ck_administrative_area_administrative_area_type CHECK (type IN ('CITY', 'DISTRICT', 'OTHER'));

-- statement-breakpoint

ALTER TABLE geo.administrative_area ALTER COLUMN geometry SET NOT NULL;
