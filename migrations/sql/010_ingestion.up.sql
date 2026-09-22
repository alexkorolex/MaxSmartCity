CREATE SCHEMA ingestion;
-- statement-breakpoint
ALTER TABLE geo.house ALTER COLUMN administrative_area_id DROP NOT NULL;
-- statement-breakpoint
ALTER TABLE geo.house ALTER COLUMN point DROP NOT NULL;
-- statement-breakpoint
CREATE TABLE ingestion.source (
    id UUID PRIMARY KEY,
    code VARCHAR(128) NOT NULL,
    url TEXT,
    data_kind VARCHAR(4) NOT NULL CHECK (data_kind IN ('REAL', 'DEMO')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_source_code UNIQUE (code)
);
-- statement-breakpoint
CREATE TABLE ingestion.house_source (
    source_id UUID NOT NULL REFERENCES ingestion.source(id),
    source_key VARCHAR(255) NOT NULL,
    house_id UUID NOT NULL REFERENCES geo.house(id),
    retrieved_at TIMESTAMPTZ NOT NULL,
    external_id VARCHAR(255),
    PRIMARY KEY (source_id, source_key)
);
-- statement-breakpoint
CREATE INDEX ix_house_source_house_id ON ingestion.house_source(house_id);
-- statement-breakpoint
CREATE TABLE ingestion.organization (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- statement-breakpoint
CREATE TABLE ingestion.organization_source (
    source_id UUID NOT NULL REFERENCES ingestion.source(id),
    source_key VARCHAR(255) NOT NULL,
    organization_id UUID NOT NULL REFERENCES ingestion.organization(id),
    retrieved_at TIMESTAMPTZ NOT NULL,
    external_id VARCHAR(255),
    PRIMARY KEY (source_id, source_key)
);
-- statement-breakpoint
CREATE INDEX ix_organization_source_organization_id ON ingestion.organization_source(organization_id);
-- statement-breakpoint
CREATE TABLE ingestion.house_organization (
    source_id UUID NOT NULL REFERENCES ingestion.source(id),
    house_id UUID NOT NULL REFERENCES geo.house(id),
    organization_id UUID NOT NULL REFERENCES ingestion.organization(id),
    relationship VARCHAR(64) NOT NULL,
    retrieved_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (source_id, house_id, organization_id, relationship)
);
-- statement-breakpoint
CREATE INDEX ix_house_organization_house_id ON ingestion.house_organization(house_id);
-- statement-breakpoint
CREATE TABLE ingestion.run (
    id UUID PRIMARY KEY,
    source_id UUID NOT NULL REFERENCES ingestion.source(id),
    file_sha256 CHAR(64) NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ,
    houses_created INTEGER NOT NULL DEFAULT 0,
    houses_updated INTEGER NOT NULL DEFAULT 0,
    organizations_created INTEGER NOT NULL DEFAULT 0,
    organizations_updated INTEGER NOT NULL DEFAULT 0,
    links_created INTEGER NOT NULL DEFAULT 0,
    error_count INTEGER NOT NULL DEFAULT 0
);
-- statement-breakpoint
CREATE TABLE ingestion.error (
    id UUID PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES ingestion.run(id),
    entity_type VARCHAR(32) NOT NULL,
    row_number INTEGER NOT NULL,
    reason TEXT NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- statement-breakpoint
CREATE INDEX ix_ingestion_error_run_id ON ingestion.error(run_id);
