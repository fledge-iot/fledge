UPDATE foglamp.configuration SET value = '{"plugin": {"description": "OMF North Plugin", "type": "string", "default": "omf", "value": "omf"}}'
        WHERE key = 'North Readings to PI';
UPDATE foglamp.configuration SET value = '{"plugin": {"description": "OMF North Plugin", "type": "string", "default": "omf", "value": "omf"}}'
        WHERE key = 'North Statistics to PI';
UPDATE foglamp.configuration SET value = '{"plugin": {"description": "OCS North Plugin", "type": "string", "default": "ocs", "value": "ocs"}}'
        WHERE key = 'North Readings to OCS';

UPDATE statistics SET key = 'SENT_1' WHERE key = 'North Readings to PI';
UPDATE statistics SET key = 'SENT_2' WHERE key = 'North Statistics to PI';
UPDATE statistics SET key = 'SENT_4' WHERE key = 'North Readings to OCS';

UPDATE foglamp.scheduled_processes SET name = 'SEND_PR_1', script = '["tasks/north", "--stream_id", "1", "--debug_level", "1"]'  WHERE name = 'North Readings to PI';
UPDATE foglamp.scheduled_processes SET name = 'SEND_PR_2', script = '["tasks/north", "--stream_id", "1", "--debug_level", "1"]'  WHERE name = 'North Statistics to PI';
UPDATE foglamp.scheduled_processes SET name = 'SEND_PR_4', script = '["tasks/north", "--stream_id", "1", "--debug_level", "1"]'  WHERE name = 'North Readings to OCS';

UPDATE foglamp.schedules SET process_name = 'SEND_PR_1' WHERE process_name = 'North Readings to PI';
UPDATE foglamp.schedules SET process_name = 'SEND_PR_2' WHERE process_name = 'North Statistics to PI';
UPDATE foglamp.schedules SET process_name = 'SEND_PR_4' WHERE process_name = 'North Readings to OCS';

DELETE from foglamp.destinations;
DELETE from foglamp.streams;

INSERT INTO foglamp.destinations ( id, description )
       VALUES ( 1, 'OMF' );
INSERT INTO foglamp.streams ( id, destination_id, description, last_object )
       VALUES ( 1, 1, 'OMF north', 0 );

INSERT INTO foglamp.streams ( id, destination_id, description, last_object )
       VALUES ( 2, 1, 'FogLAMP statistics into PI', 0 );

INSERT INTO foglamp.destinations( id, description ) VALUES ( 3, 'OCS' );
INSERT INTO foglamp.streams( id, destination_id, description, last_object ) VALUES ( 4, 3, 'OCS north', 0 );
