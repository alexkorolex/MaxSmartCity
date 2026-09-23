ALTER TABLE identity.resident DROP CONSTRAINT fk_resident_house_id_house;

-- statement-breakpoint

ALTER TABLE identity.resident DROP COLUMN house_id;
