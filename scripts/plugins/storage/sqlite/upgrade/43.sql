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

--- Insert purge system schedule and process entry
INSERT INTO fledge.scheduled_processes (name, script) VALUES ('purge_system', '["tasks/purge_system"]');
INSERT INTO fledge.schedules (id, schedule_name, process_name, schedule_type, schedule_time, schedule_interval, exclusive, enabled)
VALUES ('d37265f0-c83a-11eb-b8bc-0242ac130003', -- id
        'purge_system',                         -- schedule_name
        'purge_system',                         -- process_name
        3,                                      -- schedule_type (interval)
        NULL,                                   -- schedule_time
        '23:50:00',                             -- schedule_interval (evey 24 hours)
        't',                                    -- exclusive
        't'                                     -- enabled
    );
