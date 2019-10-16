-- updates "PIServerEndpoint" option :
--
--  "discovery" -> "Auto Discovery"
--  "piwebapi"  -> "PI Web API"
--  "cr"        -> "Connector Relay"
--

UPDATE configuration SET value = json_set(value, '$.PIServerEndpoint.options', json_array('Auto Discovery','PI Web API','Connector Relay') )
WHERE json_extract(value, '$.plugin.value') = 'PI_Server_V2';

UPDATE configuration SET value = json_set(value, '$.PIServerEndpoint.default', 'Connector Relay')
WHERE json_extract(value, '$.plugin.value') = 'PI_Server_V2';

UPDATE configuration SET value = json_set(value, '$.PIServerEndpoint.value', 'Auto Discovery')
WHERE json_extract(value, '$.plugin.value') = 'PI_Server_V2' AND
      json_extract(value, '$.PIServerEndpoint.value') = 'discovery';

UPDATE configuration SET value = json_set(value, '$.PIServerEndpoint.value', 'PI Web API')
WHERE json_extract(value, '$.plugin.value') = 'PI_Server_V2' AND
      json_extract(value, '$.PIServerEndpoint.value') = 'piwebapi';

UPDATE configuration SET value = json_set(value, '$.PIServerEndpoint.value', 'Connector Relay')
    WHERE json_extract(value, '$.plugin.value') = 'PI_Server_V2' AND
          json_extract(value, '$.PIServerEndpoint.value') = 'cr';