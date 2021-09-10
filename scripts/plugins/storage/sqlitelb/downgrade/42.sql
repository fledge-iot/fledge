DROP TABLE IF EXISTS fledge.statistics_history_daily;

DELETE FROM fledge.schedules WHERE process_name = 'purge_system';
DELETE FROM fledge.scheduled_processes WHERE name = 'purge_system';
