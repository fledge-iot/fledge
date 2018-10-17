--ALTER TABLE foglamp.schedules ADD CONSTRAINT schedules_name_uniquq UNIQUE (schedule_name);
ALTER TABLE foglamp.tasks ADD COLUMN schedule_name character varying(255);
--ALTER TABLE foglamp.tasks ADD CONSTRAINT tasks_fk2 FOREIGN KEY  ( schedule_name )
--  REFERENCES foglamp.schedules ( schedule_name ) MATCH SIMPLE
--             ON UPDATE NO ACTION
--             ON DELETE NO ACTION;
DROP INDEX IF EXISTS foglamp.tasks_ix1;
CREATE INDEX tasks_ix1
   ON foglamp.tasks(schedule_name, start_time);