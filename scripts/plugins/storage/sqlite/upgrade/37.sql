-- Scheduled process entry north microservice

INSERT INTO fledge.scheduled_processes ( name, script )
     VALUES ( 'north_C', '["services/north_C"]' );
