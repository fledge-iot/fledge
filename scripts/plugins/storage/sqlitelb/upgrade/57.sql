-- From: http://www.sqlite.org/faq.html:
--    SQLite has limited ALTER TABLE support that you can use to change type of column.
--    If you want to change the type of any column you will have to recreate the table.
--    You can save existing data to a temporary table and then drop the old table
--    Now, create the new table, then copy the data back in from the temporary table



-- Drop existing index
DROP INDEX IF EXISTS asset_tracker_ix1;
DROP INDEX IF EXISTS asset_tracker_ix2;

-- Rename existing table into a temp one
ALTER TABLE fledge.asset_tracker RENAME TO asset_tracker_old;

-- Create new table
CREATE TABLE IF NOT EXISTS fledge.asset_tracker (
       id              integer                  PRIMARY KEY AUTOINCREMENT,
       asset           character(50)            NOT NULL, -- asset name
       event           character varying(50)    NOT NULL, -- event name
       service         character varying(255)   NOT NULL, -- service name
       fledge          character varying(50)    NOT NULL, -- FL service name
       plugin          character varying(50)    NOT NULL, -- Plugin name
       deprecated_ts 				DATETIME,
       ts              DATETIME                 DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f', 'NOW', 'localtime')),
       data	       JSON			DEFAULT '{}'
);

-- Copy data
INSERT INTO fledge.asset_tracker ( id, asset, event, service, fledge, plugin, deprecated_ts, ts ) SELECT  id, asset, event, service, fledge, plugin, deprecated_ts, ts FROM fledge.asset_tracker_old;

-- Create Index
CREATE INDEX asset_tracker_ix1 ON asset_tracker (asset);
CREATE INDEX asset_tracker_ix2 ON asset_tracker (service);

-- Remote old table
DROP TABLE IF EXISTS fledge.asset_tracker_old;
