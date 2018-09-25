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
