/*
delete from foglamp.tasks;
delete from foglamp.schedules;
delete from foglamp.scheduled_processes;
*/

insert into foglamp.scheduled_processes (name, script) values ('device', '["python3", "-m", "foglamp.device"]');

/* Use this to create guids: https://www.uuidgenerator.net/version1 */

insert into foglamp.schedules(id, process_name, schedule_name, schedule_type, exclusive)
values ('ada12840-68d3-11e7-907b-a6006ad3dba0', 'device', 'device', 4, true);

/*
insert into foglamp.scheduled_processes (name, script) values ('hello', '["echo", "hello"]');
insert into foglamp.schedules(id, process_name, schedule_name, schedule_type, schedule_interval)
values ('fdad6cd6-698c-11e7-907b-a6006ad3dba0', 'hello', 'hello', 2, '00:00:05');

insert into foglamp.scheduled_processes (name, script) values ('sleep', '["sleep", "11"]');
insert into foglamp.schedules(id, process_name, schedule_name, schedule_type, schedule_interval, exclusive)
values ('fdad6cd6-698c-11e7-907b-a6006ad3dba1', 'sleep', 'sleep', 2, '00:00:10', true);

insert into foglamp.schedules(id, schedule_name, process_name, schedule_type, schedule_time,
schedule_interval, exclusive)
values ('fdad6cd6-698c-11e7-907b-a6006ad3dba3', 'timed2', 'sleep', 1, '00:00:00',
'00:01:00', true);


  any_hour          boolean not null default false, -- true distinguishes between schedule_time
                                                    -- of 00:mm:ss versus the hour when the
                                                    -- scheduler starts, especially with
                                                    -- hourly repeat

*/

