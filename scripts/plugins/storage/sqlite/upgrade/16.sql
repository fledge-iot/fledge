ALTER TABLE foglamp.configuration ADD COLUMN display_name character varying(255);
UPDATE foglamp.configuration SET display_name = key;