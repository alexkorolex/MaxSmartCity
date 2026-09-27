ALTER TABLE geo.house ADD COLUMN footprint geometry(MULTIPOLYGON,4326);

-- statement-breakpoint

ALTER TABLE geo.house ADD COLUMN geolocation_source VARCHAR(64);

-- statement-breakpoint

CREATE INDEX idx_house_footprint ON geo.house USING gist (footprint);

-- statement-breakpoint

CREATE TABLE geo.building_footprint (
	id UUID NOT NULL, 
	city VARCHAR(255) NOT NULL, 
	source VARCHAR(64) NOT NULL, 
	geometry geometry(MULTIPOLYGON,4326) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	sa_orm_sentinel INTEGER, 
	CONSTRAINT pk_building_footprint PRIMARY KEY (id)
);

-- statement-breakpoint

CREATE INDEX idx_building_footprint_geometry ON geo.building_footprint USING gist (geometry);

-- statement-breakpoint

CREATE INDEX ix_building_footprint_city_source ON geo.building_footprint (city, source);
