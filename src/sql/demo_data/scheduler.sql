insert into foglamp.scheduled_processes (name, script) values ('device', '["python3", "-m", "foglamp.device"]');

/* https://www.uuidgenerator.net/version1 */

insert into foglamp.schedules(id, process_name, schedule_name, schedule_type, schedule_interval, exclusive)
values ('ada12840-68d3-11e7-907b-a6006ad3dba0', 'device', 'device', 2, '0:0', false);





