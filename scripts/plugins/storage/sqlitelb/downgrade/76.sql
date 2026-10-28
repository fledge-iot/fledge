-- Delete the systemctl user along with its associated role
DELETE FROM fledge.users WHERE uname='systemctl';
DELETE FROM fledge.roles WHERE name ='systemctl';
-- Reset auto increment
-- You cannot use ALTER TABLE for that. The autoincrement counter is stored in a separate table named "sqlite_sequence". You can modify the value there
UPDATE sqlite_sequence SET seq = 1 WHERE name IN ('users', 'roles');
