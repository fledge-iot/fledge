-- North_Readings_to_HTTP - for readings
INSERT INTO foglamp.configuration ( key, description, value )
     VALUES ( 'North_Readings_to_HTTP',
              'HTTP North Plugin - C Code',
              ' { "plugin" : { "type" : "string", "value" : "http-north", "default" : "http-north", "description" : "Module that HTTP North Plugin will load" } } '
            );

-- North Tasks - C code
--
INSERT INTO foglamp.scheduled_processes ( name, script ) VALUES ( 'North_Readings_to_HTTP',   '["tasks/north_c"]' );

-- Readings to HTTP - C Code
INSERT INTO foglamp.schedules ( id, schedule_name, process_name, schedule_type,
                                schedule_time, schedule_interval, exclusive, enabled )
       VALUES ( 'ccdf1ef8-7e02-11e8-adc0-fa7ae01bb3bc', -- id
                'HTTP_North_C',                         -- schedule_name
                'North_Readings_to_HTTP',               -- process_name
                3,                                      -- schedule_type (interval)
                NULL,                                   -- schedule_time
                '00:00:30',                             -- schedule_interval
                't',                                    -- exclusive
                'f'                                     -- disabled
              );

-- Statistics
INSERT INTO foglamp.statistics ( key, description, value, previous_value )
     VALUES ( 'NORTH_READINGS_TO_HTTP', 'Readings sent to HTTP', 0, 0 );

