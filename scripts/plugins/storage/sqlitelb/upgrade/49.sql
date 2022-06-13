-- Add id column in category_children table

BEGIN TRANSACTION;

-- Remove existing index
DROP INDEX IF EXISTS fledge.config_children_idx1;

-- Rename existing table into a temp one
ALTER TABLE fledge.category_children RENAME TO category_children_old;

-- Create new table
CREATE TABLE fledge.category_children (
    id       integer                 PRIMARY KEY AUTOINCREMENT,
    parent   character varying(255)  NOT NULL,
    child    character varying(255)  NOT NULL
);

-- Add unique index for parent, child
CREATE UNIQUE INDEX fledge.config_children_idx1 ON category_children (parent, child);

-- Copy data
INSERT INTO fledge.category_children(parent, child) SELECT parent, child FROM fledge.category_children_old;

-- Remote temp table
DROP TABLE foglamp.category_children_old;

COMMIT;
