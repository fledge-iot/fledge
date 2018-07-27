UPDATE foglamp.configuration SET key = 'SEND_PR_1' WHERE key = 'North Readings to PI';
UPDATE foglamp.configuration SET key = 'SEND_PR_2' WHERE key = 'North Statistics to PI';
UPDATE foglamp.configuration SET key = 'SEND_PR_4' WHERE key = 'North Readings to OCS';

-- Remove DHT11 C++ south plugin entries
DELETE FROM foglamp.configuration WHERE key = 'dht11';
DELETE FROM foglamp.scheduled_processes WHERE name='dht11';
DELETE FROM foglamp.schedules WHERE process_name = 'dht11';

DELETE FROM foglamp.configuration WHERE key = 'North_Readings_to_PI';
DELETE FROM foglamp.configuration WHERE key = 'North_Statistics_to_PI';
DELETE FROM foglamp.statistics WHERE key = 'NORTH_READINGS_TO_PI';
DELETE FROM foglamp.statistics WHERE key = 'NORTH_STATISTICS_TO_PI';
DELETE FROM foglamp.scheduled_processes WHERE name = 'North_Readings_to_PI';
DELETE FROM foglamp.scheduled_processes WHERE name = 'North_Statistics_to_PI';
DELETE FROM foglamp.schedules WHERE schedule_name = 'OMF_to_PI_north_C';
DELETE FROM foglamp.schedules WHERE schedule_name = 'Stats_OMF_to_PI_north_C';
