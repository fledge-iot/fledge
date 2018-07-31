UPDATE foglamp.configuration SET value = '{"plugin": {"description": "OMF North Plugin", "type": "string", "default": "omf", "value": "omf"}, "source": {"description": "Source of data to be sent on the stream. May be either readings, statistics or audit.", "type": "string", "default": "audit", "value": "readings"}}'
        WHERE key = 'North Readings to PI';
UPDATE foglamp.configuration SET value = '{"plugin": {"description": "OMF North Plugin", "type": "string", "default": "omf", "value": "omf"}, "source": {"description": "Source of data to be sent on the stream. May be either readings, statistics or audit.", "type": "string", "default": "audit", "value": "statistics"}}'
        WHERE key = 'North Statistics to PI';
UPDATE foglamp.configuration SET value = '{"plugin": {"description": "OCS North Plugin", "type": "string", "default": "ocs", "value": "ocs"}, "source": {"description": "Source of data to be sent on the stream. May be either readings, statistics or audit.", "type": "string", "default": "audit", "value": "readings"}}'
        WHERE key = 'North Readings to OCS';

INSERT INTO foglamp.configuration ( key, description, value )
     VALUES ( 'North Audit to PI',
              'OMF North Audit Plugin',
              '{"plugin": {"description": "OMF North Plugin", "type": "string", "default": "omf", "value": "omf"}, "source": {"description": "Source of data to be sent on the stream. May be either readings, statistics or audit.", "type": "string", "default": "audit", "value": "audit"}}'
            );
INSERT INTO foglamp.statistics ( key, description, value, previous_value )
     VALUES ( 'North Audit to PI',    'Audit data sent to the historian', 0, 0 );

UPDATE statistics SET key = 'North Readings to PI' WHERE key = 'SENT_1';
UPDATE statistics SET key = 'North Statistics to PI' WHERE key = 'SENT_2';
UPDATE statistics SET key = 'North Readings to OCS' WHERE key = 'SENT_4';

UPDATE foglamp.scheduled_processes SET name = 'North Readings to PI', script = '["tasks/north"]' ) WHERE name = 'SEND_PR_1';
UPDATE foglamp.scheduled_processes SET name = 'North Statistics to PI', script = '["tasks/north"]' ) WHERE name = 'SEND_PR_2';
UPDATE foglamp.scheduled_processes SET name = 'North Readings to OCS', script = '["tasks/north"]' ) WHERE name = 'SEND_PR_4';
INSERT INTO foglamp.scheduled_processes ( name, script ) VALUES ( 'North Audit to PI',      '["tasks/north"]' );

UPDATE foglamp.schedules SET process_name = 'North Readings to PI' WHERE process_name = 'SEND_PR_1';
UPDATE foglamp.schedules SET process_name = 'North Statistics to PI' WHERE process_name = 'SEND_PR_2';
UPDATE foglamp.schedules SET process_name = 'North Readings to OCS' WHERE process_name = 'SEND_PR_4';
INSERT INTO foglamp.schedules ( id, schedule_name, process_name, schedule_type,
                                schedule_time, schedule_interval, exclusive, enabled )
       VALUES ( '9d9c329e-7dae-11e7-bb31-be2e44b06b99', -- id
                'Audit OMF to PI north',                -- schedule_name
                'North Audit to PI',                    -- process_name
                3,                                      -- schedule_type (interval)
                NULL,                                   -- schedule_time
                '00:00:30',                             -- schedule_interval
                't',                                    -- exclusive
                'f'                                     -- disabled
              );

DELETE from foglamp.destinations;
DELETE from foglamp.streams;
