
--- configuration -------------------------------------------------------------------------------------------------------

-- plugin
--
UPDATE configuration SET value = json_set(value, '$.plugin.default', 'OMF')
WHERE json_extract(value, '$.plugin.value') = 'PI_Server_V2';

UPDATE configuration SET value = json_set(value, '$.plugin.value', 'OMF')
WHERE json_extract(value, '$.plugin.value') = 'PI_Server_V2';

-- PIServerEndpoint
--
UPDATE configuration SET value = json_set(value, '$.PIServerEndpoint.options', json_array('PI Web API','Connector Relay','OSIsoft Cloud Services','Edge Data Store') )
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.PIServerEndpoint.description', 'Select the endpoint among PI Web API, Connector Relay, OSIsoft Cloud Services or Edge Data Store')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.PIServerEndpoint.order', '1')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.PIServerEndpoint.displayName', 'Endpoint')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.PIServerEndpoint.default', 'Connector Relay')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.PIServerEndpoint.value', 'Connector Relay')
WHERE json_extract(value, '$.plugin.value') = 'OMF' AND json_extract(value, '$.PIServerEndpoint.value') = 'Auto Discovery';

UPDATE configuration SET value = json_set(value, '$.PIServerEndpoint.value', 'Connector Relay')
WHERE json_extract(value, '$.plugin.value') = 'OMF' AND json_extract(value, '$.PIServerEndpoint.value') = 'cr';

UPDATE configuration SET value = json_set(value, '$.PIServerEndpoint.value', 'PI Web API')
WHERE json_extract(value, '$.plugin.value') = 'OMF' AND json_extract(value, '$.PIServerEndpoint.value') = 'piwebapi';

-- ServerHostname
-- Note: This is a new config item and its value extract from old URL config item
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

-- ServerPort
-- Note: This is a new config item and its value extract from old URL config item
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

-- URL
-- Note: Removed URL config item as it is replaced by ServerHostname & ServerPort
--
UPDATE configuration SET value = json_remove(value, '$.URL')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

-- producerToken
--
UPDATE configuration SET value = json_set(value, '$.producerToken.order', '4')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.producerToken.validity', 'PIServerEndpoint == "Connector Relay"')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

-- source
--
UPDATE configuration SET value = json_set(value, '$.source.order', '5')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

-- StaticData
--
UPDATE configuration SET value = json_set(value, '$.StaticData.order', '6')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

-- OMFRetrySleepTime
--
UPDATE configuration SET value = json_set(value, '$.OMFRetrySleepTime.order', '7')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

-- OMFMaxRetry
--
UPDATE configuration SET value = json_set(value, '$.OMFMaxRetry.order', '8')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

-- OMFHttpTimeout
--
UPDATE configuration SET value = json_set(value, '$.OMFHttpTimeout.order', '9')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

-- formatInteger
--
UPDATE configuration SET value = json_set(value, '$.formatInteger.order', '10')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

-- formatNumber
--
UPDATE configuration SET value = json_set(value, '$.formatNumber.order', '11')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

-- compression
--
UPDATE configuration SET value = json_set(value, '$.compression.order', '12')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

--  DefaultAFLocation
-- Note: This is a new config item and its default & value extract from old AFHierarchy1Level config item
--
UPDATE configuration SET value = json_set(value, '$.DefaultAFLocation.description', 'Defines the hierarchies tree in Asset Framework in which the assets will be created, each level is separated by /, PI Web API only.')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.DefaultAFLocation.type', 'string')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.DefaultAFLocation.default', json_extract(value, '$.AFHierarchy1Level.default'))
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.DefaultAFLocation.value', json_extract(value, '$.AFHierarchy1Level.value'))
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.DefaultAFLocation.order', '13')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.DefaultAFLocation.displayName', 'Asset Framework hierarchies tree')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.DefaultAFLocation.validity', 'PIServerEndpoint == "PI Web API"')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

-- AFHierarchy1Level
-- Note: Removed AFHierarchy1Level config item as it is replaced by new config item DefaultAFLocation
--
UPDATE configuration SET value = json_remove(value, '$.AFHierarchy1Level')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

-- AFMap
-- Note: This is a new config item
--
UPDATE configuration SET value = json_set(value, '$.AFMap.description', 'Defines a SET of rules to address WHERE assets should be placed in the AF hierarchy.')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.AFMap.type', 'JSON')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.AFMap.default', '{}')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.AFMap.value', '{}')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.AFMap.order', '14')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.AFMap.displayName', 'Asset Framework hierarchies rules')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.AFMap.validity', 'PIServerEndpoint == "PI Web API"')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

-- notBlockingErrors
--
UPDATE configuration SET value = json_set(value, '$.notBlockingErrors.order', '15')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

-- streamId
--
UPDATE configuration SET value = json_set(value, '$.streamId.order', '16')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

-- PIWebAPIAuthenticationMethod
--
UPDATE configuration SET value = json_set(value, '$.PIWebAPIAuthenticationMethod.order', '17')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.PIWebAPIAuthenticationMethod.validity', 'PIServerEndpoint == "PI Web API"')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

-- PIWebAPIUserId
--
UPDATE configuration SET value = json_set(value, '$.PIWebAPIUserId.order', '18')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.PIWebAPIUserId.validity', 'PIServerEndpoint == "PI Web API"')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

-- PIWebAPIPassword
--
UPDATE configuration SET value = json_set(value, '$.PIWebAPIPassword.order', '19')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.PIWebAPIPassword.validity', 'PIServerEndpoint == "PI Web API"')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

-- PIWebAPIKerberosKeytabFileName
-- Note: This is a new config item
--
UPDATE configuration SET value = json_set(value, '$.PIWebAPIKerberosKeytabFileName.description', 'Keytab file name used for Kerberos authentication in PI Web API.')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.PIWebAPIKerberosKeytabFileName.type', 'string')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.PIWebAPIKerberosKeytabFileName.default', 'piwebapi_kerberos_https.keytab')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.PIWebAPIKerberosKeytabFileName.value', 'piwebapi_kerberos_https.keytab')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.PIWebAPIKerberosKeytabFileName.displayName', 'PI Web API Kerberos keytab file')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.PIWebAPIKerberosKeytabFileName.order', '20')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.PIWebAPIKerberosKeytabFileName.validity', 'PIWebAPIAuthenticationMethod == "kerberos"')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

---
--- OCS configuration
--- NOTE- All config items are new one's for OCS
-- OCSNamespace
--
UPDATE configuration SET value = json_set(value, '$.OCSNamespace.description', 'Specifies the OCS namespace WHERE the information are stored and it is used for the interaction with the OCS API')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.OCSNamespace.type', 'string')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.OCSNamespace.default', 'name_space')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.OCSNamespace.order', '21')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.OCSNamespace.displayName', 'OCS Namespace')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.OCSNamespace.validity', 'PIServerEndpoint == "OSIsoft Cloud Services"')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.OCSNamespace.value', 'name_space')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

-- OCSTenantId
--
UPDATE configuration SET value = json_set(value, '$.OCSTenantId.description', 'Tenant id associated to the specific OCS account')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.OCSTenantId.type', 'string')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.OCSTenantId.default', 'ocs_tenant_id')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.OCSTenantId.order', '22')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.OCSTenantId.displayName', 'OCS Tenant ID')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.OCSTenantId.validity', 'PIServerEndpoint == "OSIsoft Cloud Services"')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.OCSTenantId.value', 'ocs_tenant_id')
WHERE json_extract(value, '$.plugin.value') = 'OMF';


-- OCSClientId
--
UPDATE configuration SET value = json_set(value, '$.OCSClientId.description', 'Client id associated to the specific OCS account, it is used to authenticate the source for using the OCS API')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.OCSClientId.type', 'string')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.OCSClientId.default', 'ocs_client_id')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.OCSClientId.order', '23')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.OCSClientId.displayName', 'OCS Client ID')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.OCSClientId.validity', 'PIServerEndpoint == "OSIsoft Cloud Services"')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.OCSClientId.value', 'ocs_client_id')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

-- OCSClientSecret
--
UPDATE configuration SET value = json_set(value, '$.OCSClientSecret.description', 'Client secret associated to the specific OCS account, it is used to authenticate the source for using the OCS API')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.OCSClientSecret.type', 'password')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.OCSClientSecret.default', 'ocs_client_secret')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.OCSClientSecret.order', '24')
WHERE json_extract(value, '$.plugin.value') = 'OMF';

UPDATE configuration SET value = json_set(value, '$.OCSClientSecret.displayName', 'OCS Client Secret')
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

--- asset_tracker -------------------------------------------------------------------------------------------------------
UPDATE asset_tracker SET plugin = 'OMF' WHERE plugin in ('PI_Server_V2', 'ocs_V2');
