--
-- ADD  the column: read_key   uuid
--
ALTER TABLE foglamp.readings ADD COLUMN read_key uuid UNIQUE;
UPDATE foglamp.readings SET read_key = uuid_in(md5(random()::text || clock_timestamp()::text)::cstring);
