-- Use plugin name omf
UPDATE fledge.configuration SET value = jsonb_set(value, '{plugin, value}', '"omf"') WHERE value->'plugin'->>'value' = 'pi_server';
UPDATE fledge.configuration SET value = jsonb_set(value, '{plugin, default}', '"omf"') WHERE value->'plugin'->>'default' = 'pi_server';

-- Remove PURGE_READ from Utilities parent category
DELETE FROM fledge.category_children WHERE EXISTS(SELECT 1 FROM fledge.category_children WHERE parent = 'Utilities' AND child = 'PURGE_READ');
