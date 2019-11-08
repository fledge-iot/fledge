ALTER TABLE foglamp.tasks ADD COLUMN schedule_id uuid;
DELETE FROM foglamp.tasks WHERE foglamp.tasks.schedule_name NOT IN (SELECT schedule_name FROM foglamp.schedules);
UPDATE foglamp.tasks SET schedule_id = (SELECT id FROM foglamp.schedules WHERE foglamp.tasks.schedule_name = foglamp.schedules.schedule_name AND foglamp.tasks.process_name = foglamp.schedules.process_name);
ALTER TABLE foglamp.tasks ALTER COLUMN schedule_id SET NOT NULL;