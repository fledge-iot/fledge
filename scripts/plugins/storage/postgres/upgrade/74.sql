-- Scheduled process entry for pipeline service
INSERT INTO fledge.scheduled_processes SELECT 'pipeline_c', '["services/pipeline_c"]', 90 WHERE NOT EXISTS (SELECT 1 FROM fledge.scheduled_processes WHERE name = 'pipeline_c');
