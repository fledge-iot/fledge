ALTER TABLE fledge.users ADD COLUMN failed_attempts INTEGER DEFAULT 0;
ALTER TABLE fledge.users ADD COLUMN block_until DATETIME DEFAULT "2024-01-01 10:10:10.55";
INSERT INTO fledge.log_codes ( code, description )
     VALUES ( 'USRBK', 'User Blocked' ), ( 'USRUB', 'User Unblocked' );
