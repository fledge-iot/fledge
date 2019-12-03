drop index IF EXISTS fki_readings_fk1;
create index fki_readings_fk1 on fledge.readings USING btree(asset_code, user_ts desc);
