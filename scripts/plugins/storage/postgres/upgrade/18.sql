ALTER TABLE fledge.tasks ADD COLUMN schedule_name character varying(255);
DROP INDEX IF EXISTS fledge.tasks_ix1;
CREATE INDEX tasks_ix1
   ON fledge.tasks(schedule_name, start_time);