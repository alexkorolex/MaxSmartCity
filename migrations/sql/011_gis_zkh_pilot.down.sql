ALTER TABLE ingestion.house_organization
    DROP COLUMN provenance,
    DROP COLUMN period_to,
    DROP COLUMN period_from,
    DROP COLUMN basis;
-- statement-breakpoint
DROP INDEX ingestion.ix_organization_source_inn;
-- statement-breakpoint
ALTER TABLE ingestion.organization_source
    DROP COLUMN provenance,
    DROP COLUMN ogrn,
    DROP COLUMN inn;
-- statement-breakpoint
DROP INDEX ingestion.ix_house_source_fias_id;
-- statement-breakpoint
ALTER TABLE ingestion.house_source
    DROP COLUMN provenance,
    DROP COLUMN management_method,
    DROP COLUMN official_status,
    DROP COLUMN canonical_address,
    DROP COLUMN fias_id;
