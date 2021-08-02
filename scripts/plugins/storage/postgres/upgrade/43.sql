-- Contains history of the statistics_history table
-- Data are historicized daily
--
CREATE TABLE fledge.statistics_history_daily (
                                                 year        integer NOT NULL,
                                                 day         timestamp(6) with time zone NOT NULL,
                                                 key         character varying(255)      NOT NULL,
                                                 value       bigint                      NOT NULL DEFAULT 0
);

CREATE INDEX statistics_history_daily_ix1
    ON statistics_history_daily (year);

--- statistics_history_daily ------------------------------------------------------------------:
BEGIN TRANSACTION;
INSERT INTO fledge.statistics_history_daily
(year, day, key, value)
SELECT
    EXTRACT(YEAR FROM  date(history_ts)),
    date(history_ts),
    key,
    sum("value") AS "value"
FROM fledge.statistics_history
WHERE "history_ts" < now() - INTERVAL '7 days'
GROUP BY date(history_ts), key;

DELETE FROM fledge.statistics_history WHERE "history_ts" < now() - INTERVAL '7 days';
COMMIT;
---  -----------------------------------------------------------------------------------------:

DELETE FROM fledge.tasks WHERE start_time < now() - INTERVAL '30 days';
DELETE FROM fledge.log   WHERE ts         < now() - INTERVAL '30 days';
