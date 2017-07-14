insert into foglamp.scheduled_processes (name, script) values ('device_server', '["python3", "-m", "foglamp.device"]');
insert into foglamp.scheduled_processes (name, script) values ('monkey', '["echo", "monkey", ">>", "/home/foglamp/monkey.txt"]');

/* https://www.uuidgenerator.net/version1 */

insert into foglamp.schedules(id, process_name, schedule_name, schedule_type, schedule_interval, exclusive)
values ('7c62b8f6-6843-11e7-907b-a6006ad3dba0', 'monkey', 'monkey', 0, '0:0', false)



