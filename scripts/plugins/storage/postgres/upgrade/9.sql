delete from foglamp.configuration where key in (
	'North Readings to OCS',
	'North Statistics to PI',
	'North Readings to PI',
	'North_Statistics_to_PI',
	'dht11',
	'DHT11 South C Plugin',
	'North_Readings_to_HTTP',
	'North_Readings_to_PI');

delete from foglamp.scheduled_processes where name in (
	'North Readings to OCS',
	'North Statistics to PI',
	'North Readings to PI',
	'North_Statistics_to_PI',
	'dht11',
	'DHT11 South C Plugin',
	'North_Readings_to_HTTP',
	'North_Readings_to_PI');

delete from foglamp.schedules where schedule_name in (
	'North Readings to OCS',
	'North Statistics to PI',
	'North Readings to PI',
	'North_Statistics_to_PI',
	'dht11',
	'DHT11 South C Plugin',
	'North_Readings_to_HTTP',
	'North_Readings_to_PI');

