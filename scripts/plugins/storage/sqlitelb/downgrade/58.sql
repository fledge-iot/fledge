-- Delete roles
DELETE FROM fledge.roles WHERE name IN ('view','data-view');
-- Reset auto increment
-- You cannot use ALTER TABLE for that. The autoincrement counter is stored in a separate table named "sqlite_sequence". You can modify the value there
UPDATE sqlite_sequence SET seq=1 WHERE name="roles";
