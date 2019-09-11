ALTER TABLE fledge.configuration ADD COLUMN display_name character varying(255);
UPDATE fledge.configuration SET display_name = key;