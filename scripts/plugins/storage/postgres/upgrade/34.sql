
--- configuration -------------------------------------------------------------------------------------------------------

-- plugin
--
UPDATE configuration SET value = jsonb_set(value, '{plugin, default}', '"OMF"') WHERE value->'plugin'->>'value'='PI_Server_V2';
UPDATE configuration SET value = jsonb_set(value, '{plugin, value}', '"OMF"') WHERE value->'plugin'->>'value'='PI_Server_V2';

-- PIServerEndpoint
--
UPDATE configuration SET value = jsonb_set(value, '{PIServerEndpoint, options}', $$["PI Web API","Connector Relay","OSIsoft Cloud Services","Edge Data Store"]$$) WHERE value->'plugin'->>'value'='OMF';
UPDATE configuration SET value = jsonb_set(value, '{PIServerEndpoint, description}', '"Select the endpoint among PI Web API, Connector Relay, OSIsoft Cloud Services or Edge Data Store"') WHERE value->'plugin'->>'value'='OMF';
UPDATE configuration SET value = jsonb_set(value, '{PIServerEndpoint, order}', '"1"') WHERE value->'plugin'->>'value'='OMF';
UPDATE configuration SET value = jsonb_set(value, '{PIServerEndpoint, displayName}', '"Endpoint"') WHERE value->'plugin'->>'value'='OMF';
UPDATE configuration SET value = jsonb_set(value, '{PIServerEndpoint, default}', '"Connector Relay"') WHERE value->'plugin'->>'value'='OMF';
UPDATE configuration SET value = jsonb_set(value, '{PIServerEndpoint, value}', '"Connector Relay"') WHERE value->'plugin'->>'value'='OMF' AND value->'PIServerEndpoint'->>'value'='discovery';
UPDATE configuration SET value = jsonb_set(value, '{PIServerEndpoint, value}', '"Connector Relay"') WHERE value->'plugin'->>'value'='OMF' AND value->'PIServerEndpoint'->>'value'='cr';
UPDATE configuration SET value = jsonb_set(value, '{PIServerEndpoint, value}', '"PI Web API"') WHERE value->'plugin'->>'value'='OMF' AND value->'PIServerEndpoint'->>'value'='piwebapi';

-- ServerHostname
-- Note: This is a new config item and its value extract from old URL config item
--
UPDATE configuration SET value = value || '{"ServerHostname": {"default": "localhost", "validity": "PIServerEndpoint != \"OSIsoft Cloud Services\"", "description": "Hostname of the server running the endpoint either PI Web API or Connector Relay or Edge Data Store", "displayName": "Server hostname", "type": "string", "order": "2"}}'::jsonb WHERE value->'plugin'->>'value'='OMF';

-- FIXME:
-- SELECT json_extract_path_text(value::json,'URL', 'value') FROM configuration WHERE value ->'plugin'->>'value'='OMF';
-- SELECT value->'URL'->>'value' FROM configuration WHERE value ->'plugin'->>'value'='OMF';
--UPDATE configuration SET value = jsonb_set(value, '{ServerHostname, value}', '"<>"') WHERE value ->'plugin'->>'value'='OMF';

-- ServerPort
-- Note: This is a new config item and its value extract from old URL config item
--
UPDATE configuration SET value = value || '{"ServerPort": {"default": "0", "validity": "PIServerEndpoint != \"OSIsoft Cloud Services\"", "description": "Port on which the endpoint either PI Web API or Connector Relay or Edge Data Store is listening, 0 will use the default one", "displayName": "Server port, 0=use the default", "type": "integer", "order": "3"}}'::jsonb WHERE value->'plugin'->>'value'='OMF';
-- FIXME:
--UPDATE configuration SET value = jsonb_set(value, '{ServerPort, value}', '"<>"') WHERE value ->'plugin'->>'value'='OMF';
--UPDATE configuration SET value = jsonb_set(value, '{ServerPort, value}', value->'URL'->>'value')::jsonb WHERE value ->'plugin'->>'value'='OMF';
--UPDATE configuration SET value = jsonb_set(value, '{ServerPort, value}', value->'URL')::jsonb WHERE value ->'plugin'->>'value'='OMF';


-- URL
-- Note: Removed URL config item as it is replaced by ServerHostname & ServerPort
--
UPDATE configuration SET value = value - 'URL' WHERE value ->'plugin'->>'value'='OMF';

-- producerToken
--
UPDATE configuration SET value = jsonb_set(value, '{producerToken, order}', '"4"') WHERE value->'plugin'->>'value'='OMF';
UPDATE configuration SET value = jsonb_set(value, '{producerToken, validity}', '"PIServerEndpoint == \"Connector Relay\""') WHERE value->'plugin'->>'value'='OMF';

-- source
--
UPDATE configuration SET value = jsonb_set(value, '{source, order}', '"5"') WHERE value->'plugin'->>'value'='OMF';

-- StaticData
--
UPDATE configuration SET value = jsonb_set(value, '{StaticData, order}', '"6"') WHERE value->'plugin'->>'value'='OMF';

-- OMFRetrySleepTime
--
UPDATE configuration SET value = jsonb_set(value, '{OMFRetrySleepTime, order}', '"7"') WHERE value->'plugin'->>'value'='OMF';

-- OMFMaxRetry
--
UPDATE configuration SET value = jsonb_set(value, '{OMFMaxRetry, order}', '"8"') WHERE value->'plugin'->>'value'='OMF';

-- OMFHttpTimeout
--
UPDATE configuration SET value = jsonb_set(value, '{OMFHttpTimeout, order}', '"9"') WHERE value->'plugin'->>'value'='OMF';

-- formatInteger
--
UPDATE configuration SET value = jsonb_set(value, '{formatInteger, order}', '"10"') WHERE value->'plugin'->>'value'='OMF';

-- formatNumber
--
UPDATE configuration SET value = jsonb_set(value, '{formatNumber, order}', '"11"') WHERE value->'plugin'->>'value'='OMF';

-- compression
--
UPDATE configuration SET value = jsonb_set(value, '{compression, order}', '"12"') WHERE value->'plugin'->>'value'='OMF';

--  DefaultAFLocation
-- Note: This is a new config item and its default & value extract from old AFHierarchy1Level config item
--
UPDATE configuration SET value = value || '{"DefaultAFLocation": {"validity": "PIServerEndpoint != \"PI Web API\"", "description": "Defines the hierarchies tree in Asset Framework in which the assets will be created, each level is separated by /, PI Web API only.", "displayName": "Asset Framework hierarchies tree", "type": "string", "order": "13"}}'::jsonb WHERE value->'plugin'->>'value'='OMF';
-- FIXME: This needs to be improved
UPDATE configuration SET value = jsonb_set(value, '{DefaultAFLocation, default}', (SELECT value->'AFHierarchy1Level'->'default' from configuration WHERE value ->'plugin'->>'value'='OMF')) WHERE value ->'plugin'->>'value'='OMF';
UPDATE configuration SET value = jsonb_set(value, '{DefaultAFLocation, value}', (SELECT value->'AFHierarchy1Level'->'value' from configuration WHERE value ->'plugin'->>'value'='OMF')) WHERE value ->'plugin'->>'value'='OMF';

-- AFHierarchy1Level
-- Note: Removed AFHierarchy1Level config item as it is replaced by new config item DefaultAFLocation
--
UPDATE configuration SET value = value - 'AFHierarchy1Level' WHERE value ->'plugin'->>'value'='OMF';

-- AFMap
-- Note: This is a new config item
--
UPDATE configuration SET value = value || '{"AFMap": {"default": "{}", "value": "{}", "validity": "PIServerEndpoint != \"PI Web API\"", "description": "Defines a SET of rules to address WHERE assets should be placed in the AF hierarchy.", "displayName": "Asset Framework hierarchies rules", "type": "JSON", "order": "14"}}'::jsonb WHERE value->'plugin'->>'value'='OMF';

-- notBlockingErrors
--
UPDATE configuration SET value = jsonb_set(value, '{notBlockingErrors, order}', '"15"') WHERE value->'plugin'->>'value'='OMF';

-- configuration - streamId
--
UPDATE configuration SET value = jsonb_set(value, '{streamId, order}', '"16"') WHERE value->'plugin'->>'value'='OMF';

-- configuration - PIWebAPIAuthenticationMethod
--
UPDATE configuration SET value = jsonb_set(value, '{PIWebAPIAuthenticationMethod, order}', '"17"') WHERE value->'plugin'->>'value'='OMF';
UPDATE configuration SET value = jsonb_set(value, '{PIWebAPIAuthenticationMethod, validity}', '"PIServerEndpoint != \"PI Web API\""') WHERE value->'plugin'->>'value'='OMF';

-- configuration - PIWebAPIUserId
--
UPDATE configuration SET value = jsonb_set(value, '{PIWebAPIUserId, order}', '"18"') WHERE value->'plugin'->>'value'='OMF';
UPDATE configuration SET value = jsonb_set(value, '{PIWebAPIUserId, validity}', '"PIServerEndpoint != \"PI Web API\""') WHERE value->'plugin'->>'value'='OMF';

-- configuration - PIWebAPIPassword
--
UPDATE configuration SET value = jsonb_set(value, '{PIWebAPIPassword, order}', '"19"') WHERE value->'plugin'->>'value'='OMF';
UPDATE configuration SET value = jsonb_set(value, '{PIWebAPIPassword, validity}', '"PIServerEndpoint != \"PI Web API\""') WHERE value->'plugin'->>'value'='OMF';

-- PIWebAPIKerberosKeytabFileName
-- Note: This is a new config item
--
UPDATE configuration SET value = value || '{"PIWebAPIKerberosKeytabFileName": {"default": "piwebapi_kerberos_https.keytab", "value": "piwebapi_kerberos_https.keytab", "validity": "PIWebAPIAuthenticationMethod == \"kerberos\"", "description": "Keytab file name used for Kerberos authentication in PI Web API.", "displayName": "PI Web API Kerberos keytab file", "type": "string", "order": "20"}}'::jsonb WHERE value->'plugin'->>'value'='OMF';

---
--- OCS configuration
--- NOTE- All config items are new one's for OCS
-- OCSNamespace
--
UPDATE configuration SET value = value || '{"OCSNamespace": {"default": "name_space", "value": "name_space", "validity": "PIServerEndpoint == \"OSIsoft Cloud Services\"", "description": "Specifies the OCS namespace WHERE the information are stored and it is used for the interaction with the OCS API", "displayName": "OCS Namespace", "type": "string", "order": "21"}}'::jsonb WHERE value->'plugin'->>'value'='OMF';

-- OCSTenantId
--
UPDATE configuration SET value = value || '{"OCSTenantId": {"default": "ocs_tenant_id", "value": "ocs_tenant_id", "validity": "PIServerEndpoint == \"OSIsoft Cloud Services\"", "description": "Tenant id associated to the specific OCS account", "displayName": "OCS Tenant ID", "type": "string", "order": "22"}}'::jsonb WHERE value->'plugin'->>'value'='OMF';

-- OCSClientId
--
UPDATE configuration SET value = value || '{"OCSClientId": {"default": "ocs_client_id", "value": "ocs_client_id", "validity": "PIServerEndpoint == \"OSIsoft Cloud Services\"", "description": "Client id associated to the specific OCS account, it is used to authenticate the source for using the OCS API", "displayName": "OCS Client ID", "type": "string", "order": "23"}}'::jsonb WHERE value->'plugin'->>'value'='OMF';

-- OCSClientSecret
--
UPDATE configuration SET value = value || '{"OCSClientSecret": {"default": "ocs_client_secret", "value": "ocs_client_secret", "validity": "PIServerEndpoint == \"OSIsoft Cloud Services\"", "description": "Client secret associated to the specific OCS account, it is used to authenticate the source for using the OCS API", "displayName": "OCS Client Secret", "type": "password", "order": "24"}}'::jsonb WHERE value->'plugin'->>'value'='OMF';

--- plugin_data -------------------------------------------------------------------------------------------------------
-- plugin_data
--
UPDATE plugin_data SET key = REPLACE(key,'PI_Server_V2','OMF') WHERE POSITION('PI_Server_V2' in key) > 0;

--- asset_tracker -------------------------------------------------------------------------------------------------------
UPDATE asset_tracker SET plugin = 'OMF' WHERE plugin in ('PI_Server_V2', 'ocs_V2');








