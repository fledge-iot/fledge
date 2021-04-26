ALTER TABLE fledge.users DROP COLUMN real_name;
ALTER TABLE fledge.users ALTER COLUMN access_method smallint NOT NULL DEFAULT 0;
UPDATE fledge.users SET access_method=0;
ALTER TABLE fledge.users DROP CONSTRAINT access_method_check;
