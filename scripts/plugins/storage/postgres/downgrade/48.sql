-- Remove id column in fledge.category_children
ALTER TABLE fledge.category_children DROP COLUMN IF EXISTS id;

-- Remove sequence
DROP SEQUENCE IF EXISTS fledge.category_children_id_seq;

-- Remove unique index
DROP INDEX IF EXISTS fledge.config_children_idx1;

-- Remove primary key
ALTER TABLE fledge.category_children DROP CONSTRAINT IF EXISTS config_children_pkey;

-- Add parent, child primary key
ALTER TABLE fledge.category_children ADD CONSTRAINT config_children_pkey PRIMARY KEY (parent, child);
