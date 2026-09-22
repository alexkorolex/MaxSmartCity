DROP SCHEMA ingestion CASCADE;
-- statement-breakpoint
ALTER TABLE geo.house ALTER COLUMN administrative_area_id SET NOT NULL;
-- statement-breakpoint
ALTER TABLE geo.house ALTER COLUMN point SET NOT NULL;
