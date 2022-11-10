-- Delete roles
DELETE FROM fledge.roles WHERE name IN ('view','data-view');
-- Reset auto increment
ALTER SEQUENCE fledge.roles_id_seq RESTART WITH 3