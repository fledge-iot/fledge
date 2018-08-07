-- North_Readings_to_HTTP - for readings
INSERT INTO foglamp.configuration ( key, description, value )
     VALUES ( 'North_Readings_to_HTTP',
              'HTTP North Plugin - C Code',
              ' { "plugin" : { "type" : "string", "value" : "http-north", "default" : "http-north", "description" : "Module that HTTP North Plugin will load" } } '
            );

-- North Tasks - C code
--
INSERT INTO foglamp.scheduled_processes ( name, script ) VALUES ( 'North_Readings_to_HTTP',   '["tasks/north_c"]' );
INSERT INTO foglamp.scheduled_processes ( name, script ) VALUES ( 'North_Statistics_to_HTTP', '["tasks/north_c"]' );

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

-- Statistics to HTTP - C Code
INSERT INTO foglamp.schedules ( id, schedule_name, process_name, schedule_type,
                                schedule_time, schedule_interval, exclusive, enabled )
       VALUES ( 'd1e3b377-5acb-4bde-93d5-b6a79bf76e07', -- id
                'Stats_HTTP_north_C',                   -- schedule_name
                'North_Statistics_to_HTTP',             -- process_name
                3,                                      -- schedule_type (interval)
                NULL,                                   -- schedule_time
                '00:00:30',                             -- schedule_interval
                't',                                    -- exclusive
                'f'                                     -- disabled
              );
 
