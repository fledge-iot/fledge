-- Scheduled process entry north microservice

INSERT INTO fledge.scheduled_processes SELECT 'north_C', '["services/north_C"]' WHERE NOT EXISTS (SELECT 1 FROM fledge.scheduled_processes WHERE name = 'north_C');

