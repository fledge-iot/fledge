-- Delete the systemctl user along with its associated role
DELETE FROM fledge.users WHERE uname='systemctl';
DELETE FROM fledge.roles WHERE name='systemctl';
-- Reset auto increment
ALTER SEQUENCE fledge.users_id_seq RESTART WITH 3;
ALTER SEQUENCE fledge.roles_id_seq RESTART WITH 6;