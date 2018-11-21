-- Such elaborate steps are needed because
-- From: http://www.sqlite.org/faq.html:
--    (11) How do I add or delete columns from an existing table in SQLite.
--    SQLite has limited ALTER TABLE support that you can use to add a column to the end of a table or
--    to change the name of a table. If you want to make more complex changes in the structure of a
--    table, you will have to recreate the table. You can save existing data to a temporary table, drop
--    the old table, create the new table, then copy the data back in from the temporary table.

CREATE TABLE foglamp.tasks_temporary (
             id           uuid                        NOT NULL,                          -- PK
             schedule_name character varying(255),                                       -- Name of the task
             process_name character varying(255)      NOT NULL,                          -- Name of the task's process
             state        smallint                    NOT NULL,                          -- 1-Running, 2-Complete, 3-Cancelled, 4-Interrupted
             start_time   DATETIME DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f', 'NOW', 'localtime')), -- The date and time the task started
             end_time     DATETIME,                                                      -- The date and time the task ended
             reason       character varying(255),                                        -- The reason why the task ended
             pid          integer                     NOT NULL,                          -- Linux process id
             exit_code    integer,                                                       -- Process exit status code (negative means exited via signal)
  CONSTRAINT tasks_temporary_pkey PRIMARY KEY ( id ),
  CONSTRAINT tasks_temporary_fk1 FOREIGN KEY  ( process_name )
  REFERENCES scheduled_processes ( name ) MATCH SIMPLE
             ON UPDATE NO ACTION
             ON DELETE NO ACTION );
INSERT INTO foglamp.tasks_temporary (id, process_name, state, start_time, end_time, reason, pid, exit_code) SELECT id, process_name, state, start_time, end_time, reason, pid, exit_code FROM foglamp.tasks;
DROP TABLE foglamp.tasks;

CREATE TABLE foglamp.tasks (
             id           uuid                        NOT NULL,                          -- PK
             schedule_name character varying(255),                                       -- Name of the task
             process_name character varying(255)      NOT NULL,                          -- Name of the task's process
             state        smallint                    NOT NULL,                          -- 1-Running, 2-Complete, 3-Cancelled, 4-Interrupted
             start_time   DATETIME DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f', 'NOW', 'localtime')), -- The date and time the task started
             end_time     DATETIME,                                                      -- The date and time the task ended
             reason       character varying(255),                                        -- The reason why the task ended
             pid          integer                     NOT NULL,                          -- Linux process id
             exit_code    integer,                                                       -- Process exit status code (negative means exited via signal)
  CONSTRAINT tasks_pkey PRIMARY KEY ( id ),
  CONSTRAINT tasks_fk1 FOREIGN KEY  ( process_name )
  REFERENCES scheduled_processes ( name ) MATCH SIMPLE
             ON UPDATE NO ACTION
             ON DELETE NO ACTION );
INSERT INTO foglamp.tasks SELECT id, schedule_name, process_name, state, start_time, end_time, reason, pid, exit_code FROM foglamp.tasks_temporary;
DROP TABLE foglamp.tasks_temporary;

DROP INDEX IF EXISTS tasks_ix1;
CREATE INDEX tasks_ix1
    ON tasks(schedule_name, start_time);
