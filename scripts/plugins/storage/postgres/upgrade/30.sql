-- updates "PIServerEndpoint" option :
--
--  "discovery" -> "Auto Discovery"
--  "piwebapi"  -> "PI Web API"
--  "cr"        -> "Connector Relay"
--

UPDATE configuration
SET value = jsonb_set(value, '{PIServerEndpoint, options}',  $$["Auto Discovery","PI Web API","Connector Relay"]$$)
WHERE value->'plugin'->>'value' = 'PI_Server_V2';

UPDATE configuration SET value = jsonb_set(value, '{PIServerEndpoint, default}', '"Connector Relay"')
WHERE value->'plugin'->>'value' = 'PI_Server_V2';

--
--
UPDATE configuration SET value = jsonb_set(value, '{PIServerEndpoint, value}', '"Auto Discovery"')
WHERE value->'plugin'->>'value' = 'PI_Server_V2' AND
      value->'PIServerEndpoint'->>'value' = 'discovery';

UPDATE configuration SET value = jsonb_set(value,  '{PIServerEndpoint, value}', '"PI Web API"')
WHERE value->'plugin'->>'value' = 'PI_Server_V2' AND
      value->'PIServerEndpoint'->>'value' = 'piwebapi';

UPDATE configuration SET value = jsonb_set(value,  '{PIServerEndpoint, value}', '"Connector Relay"')
WHERE value->'plugin'->>'value' = 'PI_Server_V2' AND
      value->'PIServerEndpoint'->>'value' = 'cr';
