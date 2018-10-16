--ALTER TABLE foglamp.tasks DROP CONSTRAINT schedules_name_uniquq;
--ALTER TABLE foglamp.tasks DROP CONSTRAINT tasks_fk2;
ALTER TABLE foglamp.tasks DROP COLUMN schedule_name;
--DROP INDEX IF EXISTS foglamp.tasks_ix1;
CREATE INDEX tasks_ix1
   ON foglamp.tasks(process_name, start_time);