-- Addition of id autoincrement column

-- Add sequence
CREATE SEQUENCE IF NOT EXISTS fledge.category_children_id_seq
    INCREMENT 1
    START 1
    MINVALUE 1
    MAXVALUE 9223372036854775807
    CACHE 1;

-- Remove existing primary key
ALTER TABLE fledge.category_children DROP CONSTRAINT IF EXISTS config_children_pkey;

-- Add new column as primary key
ALTER TABLE fledge.category_children ADD COLUMN id INTEGER NOT NULL DEFAULT nextval('fledge.category_children_id_seq'::regclass);

-- Add unique index for parent, child
CREATE UNIQUE INDEX IF NOT EXISTS config_children_idx1 ON fledge.category_children(parent, child);
