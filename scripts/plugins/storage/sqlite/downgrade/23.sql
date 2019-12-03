-- List of tasks
CREATE TABLE fledge.new_tasks (
             id           uuid                        NOT NULL,                          -- PK
             schedule_name character varying(255),                                       -- Name of the task
             process_name character varying(255)      NOT NULL,                          -- Name of the task's process
             state        smallint                    NOT NULL,                          -- 1-Running, 2-Complete, 3-Cancelled, 4-Interrupted
             start_time   DATETIME DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f', 'NOW', 'localtime')),	 -- The date and time the task started
             end_time     DATETIME,                                                      -- The date and time the task ended
             reason       character varying(255),                                        -- The reason why the task ended
             pid          integer                     NOT NULL,                          -- Linux process id
             exit_code    integer,                                                       -- Process exit status code (negative means exited via signal)
  CONSTRAINT tasks_pkey PRIMARY KEY ( id ),
  CONSTRAINT tasks_fk1 FOREIGN KEY  ( process_name )
  REFERENCES scheduled_processes ( name ) MATCH SIMPLE
             ON UPDATE NO ACTION
             ON DELETE NO ACTION );

DROP INDEX tasks_ix1;

DROP TABLE tasks;

ALTER TABLE new_tasks RENAME TO tasks;

-- Create index
CREATE INDEX tasks_ix1
    ON tasks(schedule_name, start_time);


-- General log table for Fledge.
CREATE TABLE fledge.new_log (
       id    INTEGER                PRIMARY KEY AUTOINCREMENT,
       code  CHARACTER(5)           NOT NULL,                  -- The process that logged the action
       level SMALLINT               NOT NULL,                  -- 0 Success - 1 Failure - 2 Warning - 4 Info
       log   JSON                   NOT NULL DEFAULT '{}',     -- Generic log structure
       ts    DATETIME DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f', 'NOW', 'localtime')),
       CONSTRAINT log_fk1 FOREIGN KEY (code)
       REFERENCES log_codes (code) MATCH SIMPLE
               ON UPDATE NO ACTION
               ON DELETE NO ACTION );

DROP INDEX log_ix1;

DROP INDEX log_ix2;

DROP TABLE log;

ALTER TABLE new_log RENAME TO log;

-- Index: log_ix1 - For queries by code
CREATE INDEX log_ix1 ON log(code, ts, level);

-- Index to make GUI response faster
CREATE INDEX log_ix2 ON log(ts);
