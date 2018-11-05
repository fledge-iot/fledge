CREATE INDEX IF NOT EXISTS log_ix2 on foglamp.log(ts);
CREATE INDEX IF NOT EXISTS tasks_ix1 on foglamp.tasks(process_name, start_time);
