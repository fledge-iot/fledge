ALTER TABLE fledge.users ADD COLUMN real_name character varying(255);
UPDATE fledge.users SET real_name='Admin user' where uname='admin';
UPDATE fledge.users SET real_name='Normal user' where uname='user';
ALTER TABLE fledge.users ALTER COLUMN access_method TYPE VARCHAR(5) NOT NULL DEFAULT 'any';
ALTER TABLE fledge.users ADD CONSTRAINT access_method_check CHECK (access_method IN ('any', 'pwd', 'cert'));
UPDATE fledge.users SET access_method='any';
