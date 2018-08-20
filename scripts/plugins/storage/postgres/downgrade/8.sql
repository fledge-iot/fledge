-- Remove from category_children
DELETE FROM foglamp.category_children WHERE parent = 'South' AND child = 'dht11';
DELETE FROM foglamp.category_children WHERE parent = 'North' AND child = 'North_Readings_to_PI';
DELETE FROM foglamp.category_children WHERE parent = 'North' AND child = 'North_Statistics_to_PI';
DELETE FROM foglamp.category_children WHERE parent = 'North' AND child = 'North_Readings_to_HTTP';
DELETE FROM foglamp.category_children WHERE parent = 'North' AND child = 'North Readings to PI';
DELETE FROM foglamp.category_children WHERE parent = 'North' AND child = 'North Statistics to PI';
DELETE FROM foglamp.category_children WHERE parent = 'North' AND child = 'North Readings to OCS';
