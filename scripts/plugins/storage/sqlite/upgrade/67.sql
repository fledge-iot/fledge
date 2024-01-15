-- Add new column name 'priority' in scheduled_processes

ALTER TABLE fledge.scheduled_processes ADD COLUMN priority INTEGER NOT NULL DEFAULT 999;
UPDATE scheduled_processes SET priority = '10' WHERE name = 'bucket_storage_c';
UPDATE scheduled_processes SET priority = '20' WHERE name = 'dispatcher_c';
UPDATE scheduled_processes SET priority = '30' WHERE name = 'notification_c';
UPDATE scheduled_processes SET priority = '100' WHERE name = 'south_c';
UPDATE scheduled_processes SET priority = '200' WHERE name in ('north_c', 'north_C');
UPDATE scheduled_processes SET priority = '300' WHERE name = 'management';
