-- Scheduled process entries for south, notification, north tasks

INSERT INTO fledge.scheduled_processes SELECT 'south_c', '["services/south_c"]' WHERE NOT EXISTS (SELECT 1 FROM fledge.scheduled_processes WHERE name = 'south_c');
INSERT INTO fledge.scheduled_processes SELECT 'notification_c', '["services/notification_c"]' WHERE NOT EXISTS (SELECT 1 FROM fledge.scheduled_processes WHERE name = 'notification_c');
INSERT INTO fledge.scheduled_processes SELECT 'north_c', '["tasks/north_c"]' WHERE NOT EXISTS (SELECT 1 FROM fledge.scheduled_processes WHERE name = 'north_c');
INSERT INTO fledge.scheduled_processes SELECT 'north', '["tasks/north"]' WHERE NOT EXISTS (SELECT 1 FROM fledge.scheduled_processes WHERE name = 'north');
