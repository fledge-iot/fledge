-- Scheduled process entry for dispatcher microservice

INSERT INTO fledge.scheduled_processes SELECT 'dispatcher_c', '["services/dispatcher_c"]' WHERE NOT EXISTS (SELECT 1 FROM fledge.scheduled_processes WHERE name = 'dispatcher_c');
