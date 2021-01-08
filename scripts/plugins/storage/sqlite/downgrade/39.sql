CREATE TABLE fledge.users_old (
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


INSERT INTO fledge.users_old (id, uname, role_id, description, pwd, public_key, enabled, pwd_last_changed, access_method) SELECT id, uname, role_id, description, pwd, public_key, enabled, pwd_last_changed, access_method FROM fledge.users;

DROP TABLE fledge.users;

ALTER TABLE fledge.users_old RENAME TO users;

CREATE INDEX fki_users_fk1 ON users (role_id);

CREATE UNIQUE INDEX users_ix1 ON users (uname);
