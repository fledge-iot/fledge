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

