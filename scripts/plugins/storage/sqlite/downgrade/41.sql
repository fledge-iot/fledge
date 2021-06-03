-- From: http://www.sqlite.org/faq.html:
--    SQLite has limited ALTER TABLE support that you can use to change type of column.
--    If you want to change the type of any column you will have to recreate the table.
--    You can save existing data to a temporary table and then drop the old table
--    Now, create the new table, then copy the data back in from the temporary table

-- Create temporary table with new changes and then copy the data from old table
DROP TABLE IF EXISTS fledge.users_temp;
CREATE TABLE fledge.users_temp (
       id                INTEGER   PRIMARY KEY AUTOINCREMENT,
       uname             character varying(80)  NOT NULL,
       role_id           integer                NOT NULL,
       description       character varying(255) NOT NULL DEFAULT '',
       pwd               character varying(255) ,
       public_key        character varying(255) ,
       enabled           boolean                NOT NULL DEFAULT 't',
       pwd_last_changed  DATETIME DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f', 'NOW', 'localtime')),
       access_method     smallint               NOT NULL DEFAULT 0,
          CONSTRAINT users_temp_fk1 FOREIGN KEY (role_id)
          REFERENCES roles (id) MATCH SIMPLE
                  ON UPDATE NO ACTION
                  ON DELETE NO ACTION );
INSERT INTO fledge.users_temp ( id, uname, pwd, enabled, pwd_last_changed, role_id, description, access_method ) SELECT id, uname, pwd, enabled, pwd_last_changed, role_id, description, 0 FROM fledge.users;

-- Recreate it again and copy the data from temp table
DROP TABLE IF EXISTS fledge.users;
CREATE TABLE fledge.users (
       id                INTEGER   PRIMARY KEY AUTOINCREMENT,
       uname             character varying(80)  NOT NULL,
       role_id           integer                NOT NULL,
       description       character varying(255) NOT NULL DEFAULT '',
       pwd               character varying(255) ,
       public_key        character varying(255) ,
       enabled           boolean                NOT NULL DEFAULT 't',
       pwd_last_changed  DATETIME DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f', 'NOW', 'localtime')),
       access_method     smallint               NOT NULL DEFAULT 0,
          CONSTRAINT users_fk1 FOREIGN KEY (role_id)
          REFERENCES roles (id) MATCH SIMPLE
                  ON UPDATE NO ACTION
                  ON DELETE NO ACTION );
INSERT INTO fledge.users ( id, uname, pwd, enabled, pwd_last_changed, role_id, description ) SELECT id, uname, pwd, enabled, pwd_last_changed, role_id, description FROM fledge.users_temp;
DROP TABLE IF EXISTS fledge.users_temp;

-- Recreate INDEX
DROP INDEX IF EXISTS fki_users_fk1;
CREATE INDEX fki_users_fk1
    ON users (role_id);

DROP INDEX IF EXISTS users_ix1;
CREATE UNIQUE INDEX users_ix1
    ON users (uname);
