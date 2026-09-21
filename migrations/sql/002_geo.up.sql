CREATE SCHEMA geo;

-- statement-breakpoint

CREATE EXTENSION IF NOT EXISTS postgis;

-- statement-breakpoint

CREATE TABLE geo.address (
	id UUID NOT NULL, 
	formatted TEXT NOT NULL, 
	city VARCHAR(255), 
	district VARCHAR(255), 
	street VARCHAR(255), 
	house_number VARCHAR(64), 
	point geography(POINT,4326), 
	sa_orm_sentinel INTEGER, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_address PRIMARY KEY (id)
);

-- statement-breakpoint

CREATE INDEX idx_address_point ON geo.address USING gist (point);

-- statement-breakpoint

CREATE TABLE geo.administrative_area (
	id UUID NOT NULL, 
	parent_id UUID, 
	name VARCHAR(255) NOT NULL, 
	type VARCHAR(8) NOT NULL, 
	geometry geometry(MULTIPOLYGON,4326) NOT NULL, 
	sa_orm_sentinel INTEGER, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_administrative_area PRIMARY KEY (id), 
	CONSTRAINT ck_administrative_area_ck_administrative_area_parent_not_self CHECK (parent_id != id), 
	CONSTRAINT fk_administrative_area_parent_id_administrative_area FOREIGN KEY(parent_id) REFERENCES geo.administrative_area (id), 
	CONSTRAINT ck_administrative_area_administrative_area_type CHECK (type IN ('CITY', 'DISTRICT', 'OTHER'))
);

-- statement-breakpoint

CREATE INDEX idx_administrative_area_geometry ON geo.administrative_area USING gist (geometry);

-- statement-breakpoint

CREATE INDEX ix_geo_administrative_area_parent_id ON geo.administrative_area (parent_id);

-- statement-breakpoint

CREATE TABLE geo.house (
	id UUID NOT NULL, 
	address_id UUID NOT NULL, 
	administrative_area_id UUID NOT NULL, 
	point geography(POINT,4326) NOT NULL, 
	external_id VARCHAR(255), 
	sa_orm_sentinel INTEGER, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_house PRIMARY KEY (id), 
	CONSTRAINT fk_house_address_id_address FOREIGN KEY(address_id) REFERENCES geo.address (id), 
	CONSTRAINT fk_house_administrative_area_id_administrative_area FOREIGN KEY(administrative_area_id) REFERENCES geo.administrative_area (id)
);

-- statement-breakpoint

CREATE INDEX idx_house_point ON geo.house USING gist (point);

-- statement-breakpoint

CREATE INDEX ix_geo_house_address_id ON geo.house (address_id);

-- statement-breakpoint

CREATE INDEX ix_geo_house_administrative_area_id ON geo.house (administrative_area_id);

-- statement-breakpoint

CREATE TABLE geo.affected_object (
	id UUID NOT NULL, 
	type VARCHAR(64) NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	address_id UUID, 
	house_id UUID, 
	point geography(POINT,4326), 
	geometry geometry(GEOMETRY,4326), 
	metadata JSONB DEFAULT '{}' NOT NULL, 
	sa_orm_sentinel INTEGER, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	CONSTRAINT pk_affected_object PRIMARY KEY (id), 
	CONSTRAINT fk_affected_object_address_id_address FOREIGN KEY(address_id) REFERENCES geo.address (id), 
	CONSTRAINT fk_affected_object_house_id_house FOREIGN KEY(house_id) REFERENCES geo.house (id)
);

-- statement-breakpoint

CREATE INDEX idx_affected_object_geometry ON geo.affected_object USING gist (geometry);

-- statement-breakpoint

CREATE INDEX idx_affected_object_point ON geo.affected_object USING gist (point);

-- statement-breakpoint

CREATE INDEX ix_geo_affected_object_address_id ON geo.affected_object (address_id);

-- statement-breakpoint

CREATE INDEX ix_geo_affected_object_house_id ON geo.affected_object (house_id);
