CREATE INDEX ix_address_normalized ON geo.address (lower(trim(city)), lower(trim(street)), lower(trim(house_number)));
