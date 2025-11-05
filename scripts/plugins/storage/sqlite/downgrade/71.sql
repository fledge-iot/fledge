ALTER TABLE fledge.users DROP COLUMN failed_attempts;
ALTER TABLE fledge.users DROP COLUMN block_until;
DELETE FROM fledge.log_codes where code IN ('USRBK', 'USRUB');
