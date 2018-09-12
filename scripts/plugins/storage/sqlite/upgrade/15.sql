CREATE INDEX IF NOT EXISTS log_ix2 ON log(ts);
CREATE INDEX IF NOT EXISTS tasks_ix1 ON tasks(process_name, start_time);
