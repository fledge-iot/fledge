delete from foglamp.tasks;
delete from foglamp.schedules;
delete from foglamp.scheduled_processes;


insert into foglamp.scheduled_processes (name, script) values ('device', '["python3", "-m", "foglamp.device"]');
insert into foglamp.schedules(id, schedule_name, process_name, schedule_type, schedule_interval, exclusive)
values ('ada12840-68d3-11e7-907b-a6006ad3dba0', 'device', 'device', 1, '0:0', true);


insert into foglamp.scheduled_processes (name, script) values ('hello', '["echo", "hello"]');
insert into foglamp.schedules(id, schedule_name, process_name, schedule_type, schedule_time, schedule_interval, exclusive)
values ('fdad6cd6-698c-11e7-907b-a6006ad3dba0', 'hello', 'hello', 2, now() + interval '1 minute', '00:00:05', true);

insert into foglamp.scheduled_processes (name, script) values ('touch', '["touch", "abc.txt"]');
insert into foglamp.schedules(id, process_name, schedule_name, schedule_type, schedule_time, schedule_interval, exclusive)
values ('fdad6cd6-698c-11e7-907b-a6006ad3dba1', 'touch', 'touch', 2, now() + interval '1 minute', '00:00:10', true);
