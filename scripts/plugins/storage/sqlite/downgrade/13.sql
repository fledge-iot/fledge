-- Use plugin name omf
UPDATE foglamp.configuration SET value = json_set(value, '$.plugin.value', 'omf') WHERE json_extract(value, '$.plugin.value') = 'pi_server';
UPDATE foglamp.configuration SET value = json_set(value, '$.plugin.default', 'omf') WHERE json_extract(value, '$.plugin.default') = 'pi_server';

-- Remove PURGE_READ from Utilities parent category
DELETE FROM foglamp.category_children WHERE EXISTS(SELECT 1 FROM foglamp.category_children WHERE parent = 'Utilities' AND child = 'PURGE_READ');
