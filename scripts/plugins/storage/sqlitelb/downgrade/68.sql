DELETE FROM fledge.schedules WHERE process_name = 'update checker';
DELETE FROM fledge.scheduled_processes WHERE name = 'update checker';

COMMIT;

