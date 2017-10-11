DELETE FROM foglamp.statistics;
INSERT INTO foglamp.statistics ( key, description, value, previous_value )
    VALUES ( 'TEST_1',   'Testing the storage service data 1', 10, 1 ),
           ( 'TEST_2',   'Testing the storage service data 2', 15, 2 );