ALTER TABLE fledge.streams ADD COLUMN audit_stats_last_object jsonb  NOT NULL DEFAULT '{"Audit":0,"Stats":0}'::jsonb;
