-- Delete role
DELETE FROM fledge.roles WHERE name='control';
-- Reset auto increment
ALTER SEQUENCE fledge.roles_id_seq RESTART WITH 5