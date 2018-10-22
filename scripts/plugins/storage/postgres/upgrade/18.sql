ALTER TABLE foglamp.tasks ADD COLUMN schedule_name character varying(255);
DROP INDEX IF EXISTS foglamp.tasks_ix1;
CREATE INDEX tasks_ix1
   ON foglamp.tasks(schedule_name, start_time);