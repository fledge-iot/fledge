UPDATE foglamp.configuration SET value = jsonb_set(value, '{source}', '{"description": "Source of data to be sent on the stream. May be either readings, statistics or audit.", "type": "string", "default": "readings", "value": "readings"}')
        WHERE key = 'North Readings to PI';

UPDATE foglamp.configuration SET value = jsonb_set(value, '{source}', '{"description": "Source of data to be sent on the stream. May be either readings, statistics or audit.", "type": "string", "default": "statistics", "value": "statistics"}')
        WHERE key = 'North Statistics to PI';

UPDATE foglamp.configuration SET value = jsonb_set(value, '{source}', '{"description": "Source of data to be sent on the stream. May be either readings, statistics or audit.", "type": "string", "default": "readings", "value": "readings"}')
        WHERE key = 'North Readings to OCS';

UPDATE statistics SET key = 'North Readings to PI' WHERE key = 'SENT_1';
UPDATE statistics SET key = 'North Statistics to PI' WHERE key = 'SENT_2';
UPDATE statistics SET key = 'North Readings to OCS' WHERE key = 'SENT_4';

---
INSERT INTO foglamp.statistics ( key , description ) VALUES ( 'Readings Sent',   'Readings Sent North' );
INSERT INTO foglamp.statistics ( key , description ) VALUES ( 'Statistics Sent',   'Statistics Sent North' );

INSERT INTO foglamp.configuration (key, description, value) VALUES ( 'North',   'North tasks' , '{}' );

UPDATE foglamp.schedules SET schedule_name=process_name WHERE process_name  in (SELECT name FROM  foglamp.scheduled_processes  WHERE script ? 'tasks/north');

INSERT INTO foglamp.category_children (parent, child)
SELECT 'North', name FROM  foglamp.scheduled_processes  WHERE script ? 'tasks/north';

INSERT INTO foglamp.scheduled_processes ( name, script ) VALUES ( 'north',   '["tasks/north"]' );

UPDATE foglamp.schedules SET process_name='north' WHERE schedule_name in (SELECT name FROM  foglamp.scheduled_processes  WHERE script ? 'tasks/north');

INSERT INTO foglamp.category_children (parent, child) VALUES ( 'North',   'OMF_TYPES' );

--- Disables North pending tasks created before the upgrade process
UPDATE tasks SET end_time=start_time, exit_code=0, state=2  WHERE end_time is null AND process_name in (SELECT name FROM  foglamp.scheduled_processes  WHERE script ? 'tasks/north');