-- Use plugin name pi_server instead of former omf
UPDATE foglamp.configuration SET value = jsonb_set(value, '{plugin, value}', '"pi_server"') WHERE value->'plugin'->>'value' = 'omf';
UPDATE foglamp.configuration SET value = jsonb_set(value, '{plugin, default}', '"pi_server"') WHERE value->'plugin'->>'default' = 'omf';

-- Insert PURGE_READ under Utilities parent category
INSERT INTO foglamp.category_children SELECT 'Utilities', 'PURGE_READ' WHERE NOT EXISTS(SELECT 1 FROM foglamp.category_children WHERE parent = 'Utilities' AND child = 'PURGE_READ');
