ALTER TABLE fledge.users ADD COLUMN failed_attempts INTEGER DEFAULT 0;
ALTER TABLE fledge.users ADD COLUMN block_until DATETIME DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f', 'NOW', 'localtime'));
INSERT INTO fledge.log_codes ( code, description )
     VALUES ( 'USRBK', 'User Blocked' ), ( 'USRUB', 'User Unblocked' );