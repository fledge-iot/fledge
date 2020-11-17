-- Scheduled process entries for south, notification, north tasks

INSERT INTO fledge.scheduled_processes ( name, script )
     VALUES ( 'south_c', '["services/south_c"]' ), ( 'notification_c', '["services/notification_c"]' ), ( 'north_c', '["tasks/north_c"]' ), ( 'north', '["tasks/north"]' );
