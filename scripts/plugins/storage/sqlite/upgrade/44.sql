UPDATE fledge.configuration SET value = json_set(value, '$.retainUnsent', json('{"description": "Retain data that has not been sent yet.", "type": "enumeration", "options":["purge unsent", "retain unsent to any destination", "retain unsent to all destinations"], "default": "purge unsent", "displayName": "Retain Unsent Data"}'))
        WHERE key = 'PURGE_READ';
