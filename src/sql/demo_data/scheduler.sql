/*
delete from foglamp.tasks;
delete from foglamp.schedules;
delete from foglamp.scheduled_processes;
*/

insert into foglamp.scheduled_processes (name, script) values ('device', '["python3", "-m", "foglamp.device"]');

/* https://www.uuidgenerator.net/version1 */

insert into foglamp.schedules(id, process_name, schedule_name, schedule_type)
values ('ada12840-68d3-11e7-907b-a6006ad3dba0', 'device', 'device', 4);

/*
insert into foglamp.scheduled_processes (name, script) values ('hello', '["echo", "hello"]');
insert into foglamp.schedules(id, process_name, schedule_name, schedule_type, schedule_interval)
values ('fdad6cd6-698c-11e7-907b-a6006ad3dba0', 'hello', 'hello', 2, '00:01:00');
*/

