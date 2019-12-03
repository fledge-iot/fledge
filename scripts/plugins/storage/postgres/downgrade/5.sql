-- Remove HTTP North C++ plugin entries
DELETE FROM fledge.configuration WHERE key = 'North_Readings_to_HTTP';
DELETE FROM fledge.scheduled_processes WHERE name='North_Readings_to_HTTP';
DELETE FROM fledge.schedules WHERE process_name = 'North_Readings_to_HTTP';
DELETE FROM fledge.statistics WHERE key = 'NORTH_READINGS_TO_HTTP';
