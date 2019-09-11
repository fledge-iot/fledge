ALTER TABLE fledge.tasks DROP COLUMN schedule_name;
CREATE INDEX tasks_ix1
   ON fledge.tasks(process_name, start_time);