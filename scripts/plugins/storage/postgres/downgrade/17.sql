ALTER TABLE foglamp.tasks DROP COLUMN schedule_name;
CREATE INDEX tasks_ix1
   ON foglamp.tasks(process_name, start_time);