-- Add new column name 'hash_algorithm' in users table

ALTER TABLE fledge.users ADD COLUMN hash_algorithm character varying(6) DEFAULT 'SHA512';
ALTER TABLE fledge.users ADD CONSTRAINT users_hash_algorithm_check CHECK (hash_algorithm IN ('SHA256', 'SHA512'));

UPDATE fledge.users SET hash_algorithm='SHA256';
UPDATE fledge.users SET pwd='495f7f5b17c534dbeabab3da2287a934b32ed6876568563b04c312be49e8773299243abd3881d13112ccfb67c4fb3ec8231406474810e1f6eb347d61c63785d4:672169c60df24b76b6b94e78cad800f8', hash_algorithm='SHA512' WHERE pwd ='39b16499c9311734c595e735cffb5d76ddffb2ebf8cf4313ee869525a9fa2c20:f400c843413d4c81abcba8f571e6ddb6';
