DROP TABLE IF EXISTS foglamp.tasks_old;

CREATE TABLE foglamp.tasks_old (
             id           uuid                        NOT NULL,                               -- PK
             schedule_name character varying(255),                                            -- Name of the task
             process_name character varying(255)      NOT NULL,                               -- Name of the task's process
             state        smallint                    NOT NULL,                               -- 1-Running, 2-Complete, 3-Cancelled, 4-Interrupted
             start_time   DATETIME DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f', 'NOW')),            -- The date and time the task started UTC
             end_time     DATETIME,                                                           -- The date and time the task ended
             reason       character varying(255),                                             -- The reason why the task ended
             pid          integer                     NOT NULL,                               -- Linux process id
             exit_code    integer,                                                            -- Process exit status code (negative means exited via signal)
  CONSTRAINT tasks_old_pkey PRIMARY KEY ( id ),
  CONSTRAINT tasks_old_fk1 FOREIGN KEY  ( process_name )
  REFERENCES scheduled_processes ( name ) MATCH SIMPLE
             ON UPDATE NO ACTION
             ON DELETE NO ACTION );

INSERT INTO foglamp.tasks_old (id, schedule_name, process_name, state, start_time, end_time, reason, pid, exit_code) SELECT id, schedule_name, process_name, state, start_time, end_time, reason, pid, exit_code FROM foglamp.tasks;
DROP TABLE IF EXISTS foglamp.tasks;

CREATE TABLE foglamp.tasks (
             id           uuid                        NOT NULL,                               -- PK
             schedule_name character varying(255),                                            -- Name of the task
             process_name character varying(255)      NOT NULL,                               -- Name of the task's process
             state        smallint                    NOT NULL,                               -- 1-Running, 2-Complete, 3-Cancelled, 4-Interrupted
             start_time   DATETIME DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f', 'NOW')),            -- The date and time the task started UTC
             end_time     DATETIME,                                                           -- The date and time the task ended
             reason       character varying(255),                                             -- The reason why the task ended
             pid          integer                     NOT NULL,                               -- Linux process id
             exit_code    integer,                                                            -- Process exit status code (negative means exited via signal)
  CONSTRAINT tasks_pkey PRIMARY KEY ( id ),
  CONSTRAINT tasks_fk1 FOREIGN KEY  ( process_name )
  REFERENCES scheduled_processes ( name ) MATCH SIMPLE
             ON UPDATE NO ACTION
             ON DELETE NO ACTION );

INSERT INTO foglamp.tasks SELECT id, schedule_name, process_name, state, start_time, end_time, reason, pid, exit_code FROM foglamp.tasks_old;
DROP TABLE IF EXISTS foglamp.tasks_old;

DROP INDEX IF EXISTS tasks_ix1;
CREATE INDEX tasks_ix1
    ON tasks(schedule_name, start_time);