UPDATE fledge.configuration SET value = json_set(value, '$.retainUnsent', json('{"description": "Retain data that has not been sent to any historian yet.", "type": "boolean",  "default": "False", "displayName": "Retain Unsent Data"}'))
        WHERE key = 'PURGE_READ';
