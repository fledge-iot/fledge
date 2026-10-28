-- Systemctl Role and User
INSERT INTO fledge.roles ( name, description )
     VALUES ('systemctl', 'It solely facilitates the execution of commands initiated by the fledge script');

INSERT INTO fledge.users ( uname, real_name, pwd, role_id, description, access_method)
     VALUES ('systemctl', 'Systemctl user', '', 6, 'User used by the systemctl scripts', 'cert');

