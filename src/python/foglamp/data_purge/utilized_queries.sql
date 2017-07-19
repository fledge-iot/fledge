-- The following are the queries being used by the Purge Process based on the `readings` table

-- Variables
--> start_time: Time which Purge process was initiated
--> age_timestamp: A Timestamp value of start_time - age
--> _LAST_ID: The last (readings) ID sent to the

-- Queries

--> DELETE
-->> Based on _LAST_ID
DELETE FROM `readings` WHERE `id` <= _LAST_ID AND `ts` < start_time;
-->> Based on age_timestamp
DELETE FROM `readings` WHERE `ts` <= age_timestamp AND `ts` < start_time;

--> SELECT
-->> Total count until Purge Process [called 2x]
SELECT COUNT(*) FROM `readings` WHERE `ts` < start_time;
-->> Total number of unsent Rows
SELECT COUNT(*) FROM `readings` WHERE `id` > _LAST_ID AND `ts` < start_time;
-->> Total number of rows that failed to get removed
-->>> Based on _LAST_ID
SELECT COUNT(*) FROM `readings` WHERE `id` <= _LAST_ID AND `ts` < start_time;
-->>> Based on age_timestamp
DELETE FROM `readings` WHERE `ts` <= age_timestamp AND `ts` < start_time;
