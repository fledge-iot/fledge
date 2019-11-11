ALTER TABLE fledge.tasks ADD COLUMN schedule_id uuid;
DELETE FROM fledge.tasks WHERE fledge.tasks.schedule_name NOT IN (SELECT schedule_name FROM fledge.schedules);
UPDATE fledge.tasks SET schedule_id = (SELECT id FROM fledge.schedules WHERE fledge.tasks.schedule_name = fledge.schedules.schedule_name AND fledge.tasks.process_name = fledge.schedules.process_name);
ALTER TABLE fledge.tasks ALTER COLUMN schedule_id SET NOT NULL;