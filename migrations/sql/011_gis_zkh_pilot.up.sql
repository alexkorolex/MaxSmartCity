ALTER TABLE ingestion.house_source
    ADD COLUMN fias_id VARCHAR(255),
    ADD COLUMN canonical_address TEXT,
    ADD COLUMN official_status VARCHAR(128),
    ADD COLUMN management_method VARCHAR(128),
    ADD COLUMN provenance JSONB NOT NULL DEFAULT '{}'::jsonb;
-- statement-breakpoint
CREATE INDEX ix_house_source_fias_id ON ingestion.house_source(fias_id) WHERE fias_id IS NOT NULL;
-- statement-breakpoint
ALTER TABLE ingestion.organization_source
    ADD COLUMN inn VARCHAR(12),
    ADD COLUMN ogrn VARCHAR(15),
    ADD COLUMN provenance JSONB NOT NULL DEFAULT '{}'::jsonb;
-- statement-breakpoint
CREATE INDEX ix_organization_source_inn ON ingestion.organization_source(inn) WHERE inn IS NOT NULL;
-- statement-breakpoint
ALTER TABLE ingestion.house_organization
    ADD COLUMN basis TEXT,
    ADD COLUMN period_from DATE,
    ADD COLUMN period_to DATE,
    ADD COLUMN provenance JSONB NOT NULL DEFAULT '{}'::jsonb;
