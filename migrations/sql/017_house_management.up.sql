CREATE TABLE geo.house_management (
	id UUID NOT NULL,
	house_id UUID NOT NULL,
	organization_id UUID NOT NULL,
	is_active BOOLEAN DEFAULT true NOT NULL,
	basis TEXT,
	assigned_via_reserve_registry BOOLEAN DEFAULT false NOT NULL,
	effective_from DATE,
	effective_to DATE,
	sa_orm_sentinel INTEGER,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
	CONSTRAINT pk_house_management PRIMARY KEY (id),
	CONSTRAINT ck_house_management_effective_range CHECK (effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from),
	CONSTRAINT fk_house_management_house_id_house FOREIGN KEY(house_id) REFERENCES geo.house (id),
	CONSTRAINT fk_house_management_organization_id_organization FOREIGN KEY(organization_id) REFERENCES identity.organization (id)
);

-- statement-breakpoint

CREATE INDEX ix_geo_house_management_house_id ON geo.house_management (house_id);

-- statement-breakpoint

CREATE INDEX ix_geo_house_management_organization_id ON geo.house_management (organization_id);

-- statement-breakpoint

CREATE UNIQUE INDEX uq_house_management_active_house ON geo.house_management (house_id) WHERE is_active;
