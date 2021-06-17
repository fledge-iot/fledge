-- Contains history of the statistics_history table
-- Data are historicized daily
--
CREATE TABLE fledge.statistics_history_daily (
                                                 year        DATE DEFAULT (STRFTIME('%Y', 'NOW')),
                                                 day         DATE DEFAULT (STRFTIME('%Y-%m-%d', 'NOW')),
                                                 key         character varying(56)       NOT NULL,
                                                 value       bigint                      NOT NULL DEFAULT 0
);

CREATE INDEX statistics_history_daily_ix1
    ON statistics_history_daily (year);

--- statistics_history_daily ------------------------------------------------------------------:
BEGIN TRANSACTION;

INSERT INTO fledge.statistics_history_daily
(year, day, key, value)
SELECT
    STRFTIME('%Y', date(history_ts)),
    date(history_ts),
    key,
    sum("value") AS "value"
FROM fledge.statistics_history
WHERE history_ts < datetime('now', '-7 days')
GROUP BY date(history_ts), key;

DELETE FROM fledge.statistics_history WHERE history_ts < datetime('now', '-7 days');
COMMIT;
---  -----------------------------------------------------------------------------------------:

DELETE FROM fledge.tasks WHERE start_time < datetime('now', '-30 days');
DELETE FROM fledge.log   WHERE ts         < datetime('now', '-30 days');
