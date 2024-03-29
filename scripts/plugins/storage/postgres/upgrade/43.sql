-- Contains history of the statistics_history table
-- Data are historicized daily
--

BEGIN TRANSACTION;

DROP INDEX IF EXISTS fledge.statistics_history_daily_ix1;
DROP TABLE IF EXISTS fledge.statistics_history_daily;

CREATE TABLE fledge.statistics_history_daily (
                                                 year        integer NOT NULL,
                                                 day         timestamp(6) with time zone NOT NULL,
                                                 key         character varying(255)      NOT NULL,
                                                 value       bigint                      NOT NULL DEFAULT 0
);

CREATE INDEX statistics_history_daily_ix1
    ON fledge.statistics_history_daily (year);

--- statistics_history_daily ------------------------------------------------------------------:

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

---  -----------------------------------------------------------------------------------------:

DELETE FROM fledge.tasks WHERE start_time < now() - INTERVAL '30 days';
DELETE FROM fledge.log   WHERE ts         < now() - INTERVAL '30 days';

--- Insert purge system schedule and process entry
DELETE FROM fledge.schedules           WHERE id   = 'd37265f0-c83a-11eb-b8bc-0242ac130003';
DELETE FROM fledge.scheduled_processes WHERE name = 'purge_system';

INSERT INTO fledge.scheduled_processes (name, script) VALUES ('purge_system', '["tasks/purge_system"]');
INSERT INTO fledge.schedules (id, schedule_name, process_name, schedule_type, schedule_time, schedule_interval, exclusive, enabled)
VALUES ('d37265f0-c83a-11eb-b8bc-0242ac130003', -- id
        'purge_system',                         -- schedule_name
        'purge_system',                         -- process_name
        3,                                      -- schedule_type (interval)
        NULL,                                   -- schedule_time
        '23:50:00',                             -- schedule_interval (evey 24 hours)
        'true',                                 -- exclusive
        'true'                                  -- enabled
    );

COMMIT;