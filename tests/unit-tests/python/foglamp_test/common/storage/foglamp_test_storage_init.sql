DELETE FROM foglamp.statistics;
INSERT INTO foglamp.statistics ( key, description, value, previous_value )
    VALUES ( 'TEST_1',   'Testing the storage service data 1', 10, 2 ),
           ( 'TEST_2',   'Testing the storage service data 2', 15, 2 );

DELETE FROM foglamp.readings;

INSERT INTO foglamp.readings(asset_code,read_key,reading)
VALUES('TEST_STORAGE_CLIENT','57179e0c-1b53-47b9-94f3-475cdba60628', '{"sensor_code_1": 10, "sensor_code_2": 1.2}');

INSERT INTO foglamp.readings(asset_code,read_key,reading)
VALUES('TEST_STORAGE_CLIENT','cc484439-b4de-493a-bf2e-27c413b00120', '{"sensor_code_1": 20, "sensor_code_2": 2.1}');

INSERT INTO foglamp.readings(asset_code,read_key,reading)
VALUES('TEST_STORAGE_CLIENT','7016622d-a4db-4ec0-8b97-85f6057317f1', '{"sensor_code_1": 80, "sensor_code_2": 5.8}');