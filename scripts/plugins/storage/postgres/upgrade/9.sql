delete from fledge.configuration where key in (
	'North Readings to OCS',
	'North Statistics to PI',
	'North Readings to PI',
	'North_Statistics_to_PI',
	'dht11',
	'DHT11 South C Plugin',
	'North_Readings_to_HTTP',
	'North_Readings_to_PI') and key not in (
		select distinct process_name from fledge.tasks);

delete from fledge.scheduled_processes where name in (
	'North Readings to OCS',
	'North Statistics to PI',
	'North Readings to PI',
	'North_Statistics_to_PI',
	'dht11',
	'DHT11 South C Plugin',
	'North_Readings_to_HTTP',
	'North_Readings_to_PI') and name not in (
		select distinct process_name from fledge.tasks);

delete from fledge.schedules where schedule_name in (
	'North Readings to OCS',
	'North Statistics to PI',
	'North Readings to PI',
	'North_Statistics_to_PI',
	'dht11',
	'DHT11 South C Plugin',
	'North_Readings_to_HTTP',
	'North_Readings_to_PI') and schedule_name not in (
		select distinct process_name from fledge.tasks);

