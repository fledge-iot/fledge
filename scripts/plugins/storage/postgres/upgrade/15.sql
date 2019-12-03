CREATE INDEX IF NOT EXISTS log_ix2 on fledge.log(ts);
CREATE INDEX IF NOT EXISTS tasks_ix1 on fledge.tasks(process_name, start_time);
