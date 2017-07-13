insert into foglamp.scheduled_processes (name, script) values ('device_server', '["python3", "-m", "foglamp.device"]');
insert into foglamp.scheduled_processes (name, script) values ('monkey', '["echo", "monkey", ">>", "/home/foglamp/monkey.txt"]');


