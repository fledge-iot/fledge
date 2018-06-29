drop index IF EXISTS foglamp.fki_readings_fk1;
create index foglamp.fki_readings_fk1 on foglamp.readings USING btree(asset_code, user_ts desc);
