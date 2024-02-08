DELETE FROM fledge.schedules WHERE process_name = 'update alerts';
DELETE FROM fledge.scheduled_processes WHERE name = 'update alerts';

COMMIT;

