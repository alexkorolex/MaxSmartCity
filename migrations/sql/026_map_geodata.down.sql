DROP TABLE geo.building_footprint;

-- statement-breakpoint

DROP INDEX geo.idx_house_footprint;

-- statement-breakpoint

ALTER TABLE geo.house DROP COLUMN geolocation_source;

-- statement-breakpoint

ALTER TABLE geo.house DROP COLUMN footprint;
