--- Insert check updates schedule and process entry

INSERT INTO fledge.scheduled_processes ( name, script ) VALUES ( 'update checker', '["tasks/check_updates"]' );
INSERT INTO fledge.schedules ( id, schedule_name, process_name, schedule_type,
                                schedule_time, schedule_interval, exclusive, enabled )
       VALUES ( '852cd8e4-3c29-440b-89ca-2c7691b0450d', -- id
                'update checker',                       -- schedule_name
                'update checker',                       -- process_name
                2,                                      -- schedule_type (timed)
                '00:05:00',                             -- schedule_time
                '00:00:00',                             -- schedule_interval
                't',                                    -- exclusive
                't'                                     -- enabled
              );
