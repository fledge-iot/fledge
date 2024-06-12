-- Create alerts table

CREATE TABLE IF NOT EXISTS fledge.alerts (
       key         character varying(80)       NOT NULL,                        -- Primary key
       message     character varying(255)      NOT NULL,                        -- Alert Message
       urgency     smallint                    NOT NULL,                        -- 1 Critical - 2 High - 3 Normal - 4 Low
       ts          timestamp(6) with time zone NOT NULL DEFAULT now(),          -- Timestamp, updated at every change
       CONSTRAINT  alerts_pkey                 PRIMARY KEY (key) );
