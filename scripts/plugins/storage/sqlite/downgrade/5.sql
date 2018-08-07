-- Remove HTTP North C++ plugin entries
DELETE FROM foglamp.configuration WHERE key = 'North_Readings_to_HTTP';
DELETE FROM foglamp.scheduled_processes WHERE name='North_Readings_to_HTTP';
DELETE FROM foglamp.scheduled_processes WHERE name='North_Statistics_to_HTTP';
DELETE FROM foglamp.schedules WHERE process_name = 'North_Readings_to_HTTP';
DELETE FROM foglamp.schedules WHERE process_name = 'North_Statistics_to_HTTP';

