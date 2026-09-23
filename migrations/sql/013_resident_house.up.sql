ALTER TABLE identity.resident ADD COLUMN house_id UUID;

-- statement-breakpoint

ALTER TABLE identity.resident ADD CONSTRAINT fk_resident_house_id_house FOREIGN KEY(house_id) REFERENCES geo.house (id);
