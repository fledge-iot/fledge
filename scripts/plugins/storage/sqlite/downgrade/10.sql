-- Statistics
INSERT INTO foglamp.statistics ( key, description, value, previous_value )
     VALUES ( 'NORTH_READINGS_TO_PI', 'Readings sent to historian', 0, 0 ),
            ( 'NORTH_STATISTICS_TO_PI', 'Statistics sent to historian', 0, 0 ),
            ( 'NORTH_READINGS_TO_HTTP', 'Readings sent to HTTP', 0, 0 ),
            ( 'North Readings to PI', 'Readings sent to the historian', 0, 0 ),
            ( 'North Statistics to PI','Statistics data sent to the historian', 0, 0 ),
            ( 'North Readings to OCS','Readings sent to OCS', 0, 0 );
