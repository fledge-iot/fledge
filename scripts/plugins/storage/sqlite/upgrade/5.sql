UPDATE foglamp.configuration SET value = '{"plugin": {"description": "OMF North Plugin", "type": "string", "default": "omf", "value": "omf"}, "source": {"description": "Source of data to be sent on the stream. May be either readings, statistics or audit.", "type": "string", "default": "audit", "value": "readings"}}'
        WHERE key = 'North Readings to PI';
UPDATE foglamp.configuration SET value = '{"plugin": {"description": "OMF North Plugin", "type": "string", "default": "omf", "value": "omf"}, "source": {"description": "Source of data to be sent on the stream. May be either readings, statistics or audit.", "type": "string", "default": "audit", "value": "statistics"}}'
        WHERE key = 'North Statistics to PI';
UPDATE foglamp.configuration SET value = '{"plugin": {"description": "OCS North Plugin", "type": "string", "default": "ocs", "value": "ocs"}, "source": {"description": "Source of data to be sent on the stream. May be either readings, statistics or audit.", "type": "string", "default": "audit", "value": "readings"}}'
        WHERE key = 'North Readings to OCS';

UPDATE statistics SET key = 'North Readings to PI' WHERE key = 'SENT_1';
UPDATE statistics SET key = 'North Statistics to PI' WHERE key = 'SENT_2';
UPDATE statistics SET key = 'North Readings to OCS' WHERE key = 'SENT_4';

UPDATE foglamp.scheduled_processes SET name = 'North Readings to PI', script = '["tasks/north"]'  WHERE name = 'SEND_PR_1';
UPDATE foglamp.scheduled_processes SET name = 'North Statistics to PI', script = '["tasks/north"]'  WHERE name = 'SEND_PR_2';
UPDATE foglamp.scheduled_processes SET name = 'North Readings to OCS', script = '["tasks/north"]'  WHERE name = 'SEND_PR_4';

UPDATE foglamp.schedules SET process_name = 'North Readings to PI' WHERE process_name = 'SEND_PR_1';
UPDATE foglamp.schedules SET process_name = 'North Statistics to PI' WHERE process_name = 'SEND_PR_2';
UPDATE foglamp.schedules SET process_name = 'North Readings to OCS' WHERE process_name = 'SEND_PR_4';

DELETE from foglamp.destinations;
DELETE from foglamp.streams;
