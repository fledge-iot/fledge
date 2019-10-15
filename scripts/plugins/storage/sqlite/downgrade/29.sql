-- updates "PIServerEndpoint" option :
--
--  "Auto Discovery"  -> "discovery"
--  "PI Web API"      -> "piwebapi"
--  "Connector Relay" -> "cr"
--

UPDATE configuration SET value = json_set(value, '$.PIServerEndpoint.options', json_array('discovery','piwebapi','cr') )
WHERE json_extract(value, '$.plugin.value') = 'PI_Server_V2';

UPDATE configuration SET value = json_set(value, '$.PIServerEndpoint.default', 'cr')
WHERE json_extract(value, '$.plugin.value') = 'PI_Server_V2';

UPDATE configuration SET value = json_set(value, '$.PIServerEndpoint.value', 'discovery')
WHERE json_extract(value, '$.plugin.value') = 'PI_Server_V2' AND
      json_extract(value, '$.PIServerEndpoint.value') = 'Auto Discovery';

UPDATE configuration SET value = json_set(value, '$.PIServerEndpoint.value', 'piwebapi')
WHERE json_extract(value, '$.plugin.value') = 'PI_Server_V2' AND
      json_extract(value, '$.PIServerEndpoint.value') = 'PI Web API';

UPDATE configuration SET value = json_set(value, '$.PIServerEndpoint.value', 'cr')
    WHERE json_extract(value, '$.plugin.value') = 'PI_Server_V2' AND
          json_extract(value, '$.PIServerEndpoint.value') = 'Connector Relay';