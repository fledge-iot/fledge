UPDATE foglamp.configuration SET key = 'SEND_PR_1' WHERE key = 'North Readings to PI';
UPDATE foglamp.configuration SET key = 'SEND_PR_2' WHERE key = 'North Statistics to PI';
UPDATE foglamp.configuration SET key = 'SEND_PR_4' WHERE key = 'North Readings to OCS';

-- Remove DHT11 C++ south plugin entries
delete from foglamp.configuration where key = 'dht11';
delete from foglamp.scheduled_processes where name='dht11';
delete from foglamp.schedules where process_name = 'dht11';
