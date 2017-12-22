--- Database commands ot insert the new plugin into FogLAMP

--- Create the south service instannce
insert into foglamp.scheduled_processes ( name, script ) values ( 'dht11pi', '["services/south"]');

--- Add the schedule to start the service at system startup
insert into foglamp.schedules(id, schedule_name, process_name, schedule_type,schedule_interval, exclusive) values ('543a59ce-a9ca-11e7-abc4-cec278b6b11a', 'device', 'dht11pi', 1, '0:0', true);

--- Insert the config needed to load the plugin
INSERT INTO foglamp.configuration ( key, description, value )
VALUES ( 'dht11pi', 'DHT11 on Raspberry Pi Configuration', '{"plugin" : { "type" : "string", "value" : "dht11pi", "default" : "dht11pi", "description" : "Plugin to load" } }');
