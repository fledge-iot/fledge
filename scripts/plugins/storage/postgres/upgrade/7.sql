-- Create the asset_tracker table
CREATE TABLE foglamp.asset_tracker (
       asset         character(50)          NOT NULL,
       event         character varying(50)  NOT NULL,
       service       character varying(255) NOT NULL,
       foglamp       character varying(50)  NOT NULL,
       plugin        character varying(50)  NOT NULL,
       ts            timestamp(6) with time zone NOT NULL DEFAULT now() );