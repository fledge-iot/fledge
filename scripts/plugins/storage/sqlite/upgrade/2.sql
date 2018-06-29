drop index foglamp.fki_readings_fk1;
create index foglamp.fki_readings.fk1 on foglamp.readings(asset_code, user_ts desc);
