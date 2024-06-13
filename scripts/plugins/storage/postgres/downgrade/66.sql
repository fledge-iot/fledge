--Remove priority column from scheduled_processes table
ALTER TABLE fledge.scheduled_processes DROP COLUMN IF EXISTS priority;
