-- Remove 'hash_algorithm' column from users table

ALTER TABLE fledge.users DROP COLUMN hash_algorithm;
ALTER TABLE fledge.users DROP CONSTRAINT users_hash_algorithm_check;
UPDATE fledge.users SET pwd='39b16499c9311734c595e735cffb5d76ddffb2ebf8cf4313ee869525a9fa2c20:f400c843413d4c81abcba8f571e6ddb6' WHERE pwd ='495f7f5b17c534dbeabab3da2287a934b32ed6876568563b04c312be49e8773299243abd3881d13112ccfb67c4fb3ec8231406474810e1f6eb347d61c63785d4:672169c60df24b76b6b94e78cad800f8';
