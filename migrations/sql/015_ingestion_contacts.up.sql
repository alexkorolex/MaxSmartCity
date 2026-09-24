ALTER TABLE ingestion.organization_source
    ADD COLUMN phones JSONB NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN email VARCHAR(320),
    ADD COLUMN website TEXT;
