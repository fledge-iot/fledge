ALTER TABLE fledge.streams ADD COLUMN last_objects jsonb  NOT NULL DEFAULT '{"Readings":0,"Stats":0,"Audit":0}'::jsonb;
