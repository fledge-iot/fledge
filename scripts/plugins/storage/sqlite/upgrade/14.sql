-- Use plugin name pi_server instead of former omf
UPDATE fledge.configuration SET value = json_set(value, '$.plugin.value', 'pi_server') WHERE json_extract(value, '$.plugin.value') = 'omf';
UPDATE fledge.configuration SET value = json_set(value, '$.plugin.default', 'pi_server') WHERE json_extract(value, '$.plugin.default') = 'omf';

-- Insert PURGE_READ under Utilities parent category
INSERT INTO fledge.category_children SELECT 'Utilities', 'PURGE_READ' WHERE NOT EXISTS(SELECT 1 FROM fledge.category_children WHERE parent = 'Utilities' AND child = 'PURGE_READ');
