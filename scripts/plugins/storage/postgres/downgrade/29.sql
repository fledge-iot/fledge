-- updates "PIServerEndpoint" option :
--
--  "Auto Discovery"  -> "discovery"
--  "PI Web API"      -> "piwebapi"
--  "Connector Relay" -> "cr"
--
UPDATE configuration
SET value = jsonb_set(value, '{PIServerEndpoint, options}',  $$["discovery","piwebapi","cr"]$$)
WHERE value->'plugin'->>'value' = 'PI_Server_V2';

UPDATE configuration SET value = jsonb_set(value, '{PIServerEndpoint, default}', '"cr"')
WHERE value->'plugin'->>'value' = 'PI_Server_V2';

--
--
UPDATE configuration SET value = jsonb_set(value, '{PIServerEndpoint, value}', '"discovery"')
WHERE value->'plugin'->>'value' = 'PI_Server_V2' AND
      value->'PIServerEndpoint'->>'value' = 'Auto Discovery';

UPDATE configuration SET value = jsonb_set(value,  '{PIServerEndpoint, value}', '"piwebapi"')
WHERE value->'plugin'->>'value' = 'PI_Server_V2' AND
      value->'PIServerEndpoint'->>'value' = 'PI Web API';

UPDATE configuration SET value = jsonb_set(value,  '{PIServerEndpoint, value}', '"cr"')
WHERE value->'plugin'->>'value' = 'PI_Server_V2' AND
      value->'PIServerEndpoint'->>'value' = 'Connector Relay';
