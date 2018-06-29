drop index IF EXISTS fki_readings_fk1;
create index fki_readings_fk1 on readings(asset_code, user_ts desc);
