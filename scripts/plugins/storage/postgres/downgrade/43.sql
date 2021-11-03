
UPDATE fledge.configuration SET value = jsonb_set(value, '{retainUnsent}', '{"description": "Retain data that has not been sent yet.", "type": "enumeration", "options":["purge unsent", "retain unsent to any destination", "retain unsent to all destinations"], "default": "purge unsent", "displayName": "Retain Unsent Data","value": "false"}')
        WHERE key = 'PURGE_READ' AND
              value->'retainUnsent'->>'value' = 'purge unsent';

UPDATE fledge.configuration SET value = jsonb_set(value, '{retainUnsent}', '{"description": "Retain data that has not been sent yet.", "type": "enumeration", "options":["purge unsent", "retain unsent to any destination", "retain unsent to all destinations"], "default": "purge unsent", "displayName": "Retain Unsent Data","value": "true"}')
        WHERE  key = 'PURGE_READ' AND
               value->'retainUnsent'->>'value' = 'retain unsent to all destinations';

UPDATE fledge.configuration SET value = jsonb_set(value, '{retainUnsent}', '{"description": "Retain data that has not been sent yet.", "type": "enumeration", "options":["purge unsent", "retain unsent to any destination", "retain unsent to all destinations"], "default": "purge unsent", "displayName": "Retain Unsent Data","value": "true"}')
        WHERE  key = 'PURGE_READ' AND
               value->'retainUnsent'->>'value' = 'retain unsent to any destination';
