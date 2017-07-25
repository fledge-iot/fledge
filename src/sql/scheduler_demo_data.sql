delete from foglamp.tasks where process_name in ('hello', 'touch');
delete from foglamp.schedules where process_name in ('hello', 'touch');
delete from foglamp.scheduled_processes where name in ('hello', 'touch');

insert into foglamp.scheduled_processes (name, script) values ('hello', '["echo", "hello"]');
insert into foglamp.schedules(id, schedule_name, process_name, schedule_type, schedule_time, schedule_interval, exclusive)
values ('fdad6cd6-698c-11e7-907b-a6006ad3dba0', 'hello', 'hello', 2, now() + interval '1 minute', '00:00:05', true);

insert into foglamp.scheduled_processes (name, script) values ('touch', '["touch", "abc.txt"]');
insert into foglamp.schedules(id, process_name, schedule_name, schedule_type, schedule_time, schedule_interval, exclusive)
values ('fdad6cd6-698c-11e7-907b-a6006ad3dba1', 'touch', 'touch', 2, now() + interval '1 minute', '00:00:10', true);
