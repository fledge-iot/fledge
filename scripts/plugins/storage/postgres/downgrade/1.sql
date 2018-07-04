drop index if exists fki_readings_fk1;
CREATE INDEX fki_readings_fk1
    ON foglamp.readings USING btree (asset_code);

