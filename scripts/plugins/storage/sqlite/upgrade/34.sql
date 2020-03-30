
--- configuration -------------------------------------------------------------------------------------------------------

-- configuration - PIServerEndpoint
--
UPDATE configuration SET
    value = json_set(value, '$.PIServerEndpoint.options', json_array('PI Web API','Connector Relay','OSIsoft Cloud Services','Edge Data Store') )
WHERE json_extract(value, '$.plugin.value') = 'PI_Server_V2';

UPDATE configuration SET
    value = json_set(value, '$.PIServerEndpoint.description', 'Select the endpoint among PI Web API, Connector Relay, OSIsoft Cloud Services or Edge Data Store')
WHERE json_extract(value, '$.plugin.value') = 'PI_Server_V2';

UPDATE configuration SET
    value = json_set(value, '$.PIServerEndpoint.order', '1')
WHERE json_extract(value, '$.plugin.value') = 'PI_Server_V2';

UPDATE configuration SET
    value = json_set(value, '$.PIServerEndpoint.displayName', 'Endpoint')
WHERE json_extract(value, '$.plugin.value') = 'PI_Server_V2';

UPDATE configuration SET value = json_set(value, '$.PIServerEndpoint.value', 'Connector Relay')
WHERE json_extract(value, '$.plugin.value') = 'PI_Server_V2' AND
        json_extract(value, '$.PIServerEndpoint.value') = 'Auto Discovery';

UPDATE configuration SET value = json_set(value, '$.plugin.default', 'OMF')
WHERE json_extract(value, '$.plugin.value') = 'PI_Server_V2';

UPDATE configuration SET value = json_set(value, '$.plugin.value', 'OMF')
WHERE json_extract(value, '$.plugin.value') = 'PI_Server_V2';

-- configuration - ServerHostname
--
UPDATE configuration SET value = json_set(value, '$.ServerHostname.description', 'Hostname of the server running the endpoint either PI Web API or Connector Relay or Edge Data Store')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.ServerHostname.type', 'string')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.ServerHostname.default', 'localhost')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.ServerHostname.order', '2')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.ServerHostname.displayName', 'Server hostname')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.ServerHostname.validity', 'PIServerEndpoint != "OSIsoft Cloud Services"')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value =
    json_set(
            value,
            '$.ServerHostname.value',
            substr(json_extract(value, '$.URL.value'),
                   instr(json_extract(value, '$.URL.value'), '://') + 3,
                   instr(REPLACE(json_extract(value, '$.URL.value'), '://', 'xxx'), ':') -
                   instr(json_extract(value, '$.URL.value'), '://') - 3)
    )
WHERE json_extract(value, '$.plugin.value') = 'OMF';

-- configuration - ServerPort
--
UPDATE configuration SET value = json_set(value, '$.ServerPort.description', 'Port on which the endpoint either PI Web API or Connector Relay or Edge Data Store is listening, 0 will use the default one')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.ServerPort.type', 'integer')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.ServerPort.default', '0')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.ServerPort.order', '3')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.ServerPort.displayName', 'Server port, 0=use the default')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.ServerPort.validity', 'PIServerEndpoint != "OSIsoft Cloud Services"')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value =
     json_set(
             value,
             '$.ServerPort.value',
             substr(json_extract(value, '$.URL.value'),
                    instr(REPLACE(json_extract(value, '$.URL.value'), '://', 'xxx'), ':') + 1,
                    instr(REPLACE(json_extract(value, '$.URL.value'), '://', 'xxx'), '/') -
                    instr(REPLACE(json_extract(value, '$.URL.value'), '://', 'xxx'), ':') - 1
                 )
    )
WHERE json_extract(value, '$.plugin.value') = 'OMF';


-- configuration - URL
--
UPDATE configuration SET value = json_remove(value, '$.URL')
WHERE json_extract(value, '$.plugin.value') = 'OMF';


-- configuration - producerToken
--
UPDATE configuration SET value = json_set(value, '$.producerToken.order', '4')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.producerToken.validity', 'PIServerEndpoint == "Connector Relay"')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

-- configuration - source
--
UPDATE configuration SET value = json_set(value, '$.source.order', '5')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

-- configuration - StaticData
--
UPDATE configuration SET value = json_set(value, '$.StaticData.order', '6')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

-- configuration - OMFRetrySleepTime
--
UPDATE configuration SET value = json_set(value, '$.OMFRetrySleepTime.order', '7')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

-- configuration - OMFMaxRetry
--
UPDATE configuration SET value = json_set(value, '$.OMFMaxRetry.order', '8')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

-- configuration - OMFHttpTimeout
--
UPDATE configuration SET value = json_set(value, '$.OMFHttpTimeout.order', '9')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

-- configuration - formatInteger
--
UPDATE configuration SET value = json_set(value, '$.formatInteger.order', '10')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

-- configuration - formatNumber
--
UPDATE configuration SET value = json_set(value, '$.formatNumber.order', '11')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

-- configuration - compression
--
UPDATE configuration SET value = json_set(value, '$.compression.order', '12')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

-- configuration - DefaultAFLocation
--
UPDATE configuration SET value = json_set(value, '$.DefaultAFLocation.order', '13')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.DefaultAFLocation.validity', 'PIServerEndpoint == "PI Web API"')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

-- configuration - AFMap
--
UPDATE configuration SET value = json_set(value, '$.AFMap.order', '14')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.AFMap.validity', 'PIServerEndpoint == "PI Web API"')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

-- configuration - notBlockingErrors
--
UPDATE configuration SET value = json_set(value, '$.notBlockingErrors.order', '15')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

-- configuration - streamId
--
UPDATE configuration SET value = json_set(value, '$.streamId.order', '16')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

-- configuration - PIWebAPIAuthenticationMethod
--
UPDATE configuration SET value = json_set(value, '$.PIWebAPIAuthenticationMethod.order', '17')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.PIWebAPIAuthenticationMethod.validity', 'PIServerEndpoint == "PI Web API"')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

-- configuration - PIWebAPIUserId
--
UPDATE configuration SET value = json_set(value, '$.PIWebAPIUserId.order', '18')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

-- configuration - PIWebAPIPassword
--
UPDATE configuration SET value = json_set(value, '$.PIWebAPIPassword.order', '19')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

-- configuration - PIWebAPIKerberosKeytabFileName
--
UPDATE configuration SET value = json_set(value, '$.PIWebAPIKerberosKeytabFileName.order', '20')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

---
--- OCS configurations
---


-- configuration - OCSNamespace
--
UPDATE configuration SET
    value = json_set(value, '$.OCSNamespace.description', 'Specifies the OCS namespace where the information are stored and it is used for the interaction with the OCS API')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.OCSNamespace.type', 'string')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.OCSNamespace.default', 'name_space')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.OCSNamespace.order', '21')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET
    value = json_set(value, '$.OCSNamespace.displayName', 'OCS Namespace')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.OCSNamespace.validity', 'PIServerEndpoint == "OSIsoft Cloud Services"')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.OCSNamespace.value', 'name_space')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

-- configuration - OCSTenantId
--
UPDATE configuration SET
    value = json_set(value, '$.OCSTenantId.description', 'Tenant id associated to the specific OCS account')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.OCSTenantId.type', 'string')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.OCSTenantId.default', 'ocs_tenant_id')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.OCSTenantId.order', '22')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET
    value = json_set(value, '$.OCSTenantId.displayName', 'OCS Tenant ID')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.OCSTenantId.validity', 'PIServerEndpoint == "OSIsoft Cloud Services"')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.OCSTenantId.value', 'ocs_tenant_id')
WHERE json_extract(value, '$.plugin.value') = 'OMF';


-- configuration - OCSClientId
--
UPDATE configuration SET
    value = json_set(value, '$.OCSClientId.description', 'Client id associated to the specific OCS account, it is used to authenticate the source for using the OCS API')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.OCSClientId.type', 'string')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.OCSClientId.default', 'ocs_client_id')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.OCSClientId.order', '23')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET
    value = json_set(value, '$.OCSClientId.displayName', 'OCS Client ID')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.OCSClientId.validity', 'PIServerEndpoint == "OSIsoft Cloud Services"')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.OCSClientId.value', 'ocs_client_id')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

-- configuration - OCSClientSecret
--
UPDATE configuration SET
    value = json_set(value, '$.OCSClientSecret.description', 'Client secret associated to the specific OCS account, it is used to authenticate the source for using the OCS API')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.OCSClientSecret.type', 'password')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.OCSClientSecret.default', 'ocs_client_secret')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.OCSClientSecret.order', '24')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET
    value = json_set(value, '$.OCSClientSecret.displayName', 'OCS Client Secret')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.OCSClientSecret.validity', 'PIServerEndpoint == "OSIsoft Cloud Services"')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.OCSClientSecret.value', 'ocs_client_secret')
WHERE json_extract(value, '$.plugin.value') = 'OMF';



--- plugin_data -------------------------------------------------------------------------------------------------------
-- plugin_data
--
UPDATE plugin_data SET key = REPLACE(key,'PI_Server_V2','OMF')
WHERE instr(key, 'PI_Server_V2') > 0;

