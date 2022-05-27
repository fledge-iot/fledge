-- Scheduled process entry for BucketStorage microservice

INSERT INTO fledge.scheduled_processes SELECT 'bucket_storage_c', '["services/bucket_storage_c"]' WHERE NOT EXISTS (SELECT 1 FROM fledge.scheduled_processes WHERE name = 'bucket_storage_c');
