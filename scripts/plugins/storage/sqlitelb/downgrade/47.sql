DELETE FROM fledge.schedules WHERE process_name = 'bucket_storage_c';
DELETE FROM fledge.scheduled_processes WHERE name = 'bucket_storage_c';
