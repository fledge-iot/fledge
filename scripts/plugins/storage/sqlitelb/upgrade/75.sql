ALTER TABLE fledge.streams ADD COLUMN stats_last_object bigint DEFAULT 0;
ALTER TABLE fledge.streams ADD COLUMN audit_last_object bigint DEFAULT 0;
