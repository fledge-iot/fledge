UPDATE fledge.configuration SET value = json_set(value, '$.retainUnsent', json('{"description": "Retain data that has not been sent to any historian yet.", "type": "boolean",  "default": "false", "displayName": "Retain Unsent Data", "value": "false"}'))
        WHERE key = 'PURGE_READ' AND
               json_extract(value, '$.retainUnsent.value')  = "purge unsent";


UPDATE fledge.configuration SET value = json_set(value, '$.retainUnsent', json('{"description": "Retain data that has not been sent to any historian yet.", "type": "boolean",  "default": "false", "displayName": "Retain Unsent Data", "value": "true"}'))
        WHERE key = 'PURGE_READ' AND
               json_extract(value, '$.retainUnsent.value')  = "retain unsent to all destinations";

UPDATE fledge.configuration SET value = json_set(value, '$.retainUnsent', json('{"description": "Retain data that has not been sent to any historian yet.", "type": "boolean",  "default": "false", "displayName": "Retain Unsent Data", "value": "true"}'))
        WHERE key = 'PURGE_READ' AND
               json_extract(value, '$.retainUnsent.value')  = "retain unsent to any destination";

