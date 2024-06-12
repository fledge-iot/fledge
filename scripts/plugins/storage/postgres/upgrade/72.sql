ALTER TABLE fledge.users ADD COLUMN failed_attempts integer DEFAULT 0;
ALTER TABLE fledge.users ADD COLUMN block_until timestamp(6)  DEFAULT now();
INSERT INTO fledge.log_codes ( code, description )
     VALUES ( 'USRBK', 'User Blocked' ), ( 'USRUB', 'User Unblocked' );
