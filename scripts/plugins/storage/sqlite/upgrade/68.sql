-- Create alerts table

CREATE TABLE IF NOT EXISTS fledge.alerts (
       key         character varying(80)       NOT NULL,                                  -- Primary key
       message     character varying(255)      NOT NULL,                                 -- Alert Message
       urgency     SMALLINT                    NOT NULL,                                 -- 1 Critical - 2 High - 3 Normal - 4 Low
       ts          DATETIME    DEFAULT (STRFTIME('%Y-%m-%d %H:%M:%f+00:00', 'NOW')),     -- Timestamp, updated at every change
       CONSTRAINT  alerts_pkey PRIMARY KEY (key) );
