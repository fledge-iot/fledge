-- Remove id column in fledge.category_children

BEGIN TRANSACTION;

-- Drop existing index
DROP INDEX IF EXISTS fledge.config_children_idx1;

-- Rename existing table into a temp one
ALTER TABLE fledge.category_children RENAME TO category_children_old;

-- Create new table
CREATE TABLE fledge.category_children (
       parent   character varying(255)  NOT NULL,
       child    character varying(255)  NOT NULL,
       CONSTRAINT config_children_pkey PRIMARY KEY(parent, child)
);

-- Copy data
INSERT INTO fledge.category_children(parent, child) SELECT parent, child FROM fledge.category_children_old;

-- Remote temp table
DROP TABLE IF EXISTS fledge.category_children_old;

COMMIT;
