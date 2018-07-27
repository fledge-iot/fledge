UPDATE foglamp.configuration SET key = 'North Readings to PI' WHERE key = 'SEND_PR_1';
UPDATE foglamp.configuration SET key = 'North Statistics to PI' WHERE key = 'SEND_PR_2';
UPDATE foglamp.configuration SET key = 'North Readings to OCS' WHERE key = 'SEND_PR_4';

-- Insert entries for DHT11 C++ south plugin

INSERT INTO foglamp.configuration ( key, description, value )
     VALUES ( 'dht11',
              'DHT11 South C Plugin',
              ' { "plugin" : { "type" : "string", "value" : "dht11", "default" : "dht11", "description" : "Module that DHT11 South Plugin will load" } } '
            );

INSERT INTO foglamp.scheduled_processes ( name, script ) VALUES ( 'dht11',   '["services/south_c"]' );

INSERT INTO foglamp.schedules ( id, schedule_name, process_name, schedule_type,
                                schedule_time, schedule_interval, exclusive, enabled )
       VALUES ( '6b25f4d9-c7f3-4fc8-bd4a-4cf79f7055ca', -- id
                'dht11',                                -- schedule_name
                'dht11',                                -- process_name
                1,                                      -- schedule_type (interval)
                NULL,                                   -- schedule_time
                '01:00:00',                             -- schedule_interval (evey hour)
                't',                                    -- exclusive
                'f'                                     -- enabled
              );

-- North_Readings_to_PI - OMF Translator for readings - C Code
INSERT INTO foglamp.configuration ( key, description, value )
     VALUES ( 'North_Readings_to_PI',
              'OMF North Plugin - C Code',
              ' { "plugin" : { "type" : "string", "value" : "omf", "default" : "omf", "description" : "Module that OMF North Plugin will load" } } '
            );

-- North_Statistics_to_PI - OMF Translator for statistics - C Code
INSERT INTO foglamp.configuration ( key, description, value )
     VALUES ( 'North_Statistics_to_PI',
              'OMF North Plugin - C Code',
              ' { "plugin" : { "type" : "string", "value" : "omf", "default" : "omf", "description" : "Module that OMF North Plugin will load" } } '
            );

-- North Tasks - C code
INSERT INTO foglamp.scheduled_processes ( name, script ) VALUES ( 'North_Readings_to_PI',   '["tasks/north_c"]' );
INSERT INTO foglamp.scheduled_processes ( name, script ) VALUES ( 'North_Statistics_to_PI', '["tasks/north_c"]' );

-- Readings OMF to PI - C Code
INSERT INTO foglamp.schedules ( id, schedule_name, process_name, schedule_type,
                                schedule_time, schedule_interval, exclusive, enabled )
       VALUES ( '1cdf1ef8-7e02-11e8-adc0-fa7ae01bbebc', -- id
                'OMF_to_PI_north_C',                    -- schedule_name
                'North_Readings_to_PI',                 -- process_name
                3,                                      -- schedule_type (interval)
                NULL,                                   -- schedule_time
                '00:00:30',                             -- schedule_interval
                't',                                    -- exclusive
                'f'                                     -- disabled
              );

-- Statistics OMF to PI - C Code
INSERT INTO foglamp.schedules ( id, schedule_name, process_name, schedule_type,
                                schedule_time, schedule_interval, exclusive, enabled )
       VALUES ( 'f1e3b377-5acb-4bde-93d5-b6a792f76e07', -- id
                'Stats_OMF_to_PI_north_C',              -- schedule_name
                'North_Statistics_to_PI',               -- process_name
                3,                                      -- schedule_type (interval)
                NULL,                                   -- schedule_time
                '00:00:30',                             -- schedule_interval
                't',                                    -- exclusive
                'f'                                     -- disabled
              );
-- Statistics
INSERT INTO foglamp.statistics ( key, description, value, previous_value ) VALUES ( 'NORTH_READINGS_TO_PI', 'Statistics sent to historian', 0, 0 );
INSERT INTO foglamp.statistics ( key, description, value, previous_value ) VALUES ( 'NORTH_STATISTICS_TO_PI', 'Statistics sent to historian', 0, 0 );
