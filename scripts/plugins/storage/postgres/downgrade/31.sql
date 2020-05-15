--
-- ADD  the column: read_key   uuid
--
ALTER TABLE fledge.readings ADD COLUMN read_key uuid UNIQUE;
UPDATE fledge.readings SET read_key = uuid_in(md5(random()::text || clock_timestamp()::text)::cstring);
