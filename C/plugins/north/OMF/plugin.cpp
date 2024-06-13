/*
 * Fledge PI Server north plugin.
 *
 * Copyright (c) 2018-2022 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Massimiliano Pinto, Stefano Simonelli
 *
 * PI Web API OMF Endpoint documentation available at:
 * https://fledge-iot.readthedocs.io/en/latest/OMF.html?highlight=omf%20hint#
 *
 * Troubleshooting the PI-Server integration available at:
 * https://fledge-iot.readthedocs.io/en/latest/troubleshooting_pi-server_integration.html#how-to-check-the-pi-web-api-is-installed-and-running
 *
 * Information about Asset Framework Hierarchy Rules available at:
 * https://fledge-iot.readthedocs.io/en/latest/OMF.html?highlight=omf%20hint#asset-framework-hierarchy-rules
 *
 * Information about OMF Hint available at:
 * https://fledge-iot.readthedocs.io/en/latest/OMF.html?highlight=omf%20hint#omf-hints
 * https://fledge-iot.readthedocs.io/en/latest/plugins/fledge-filter-omfhint/index.html
 *
 * OSIsoft documentation about PI Web API:
 * https://docs.osisoft.com/bundle/pi-web-api/page/pi-web-api.html
 * https://docs.osisoft.com/bundle/pi-web-api-reference/page/help.html
 * https://pisquare.osisoft.com/s/topic/0TO1I000000OGBGWA4/pi-web-api
 *
 * OSIsoft documentation about OMF:
 * https://docs.osisoft.com/bundle/omf/page/index.html
 *
 * OSIsoft documentation about OMF in PI Web API:
 * https://docs.osisoft.com/bundle/omf-with-pi-web-api/page/osisoft-message-format.html
 *
 */

#include <unistd.h>

#include <plugin_api.h>
#include <stdio.h>
#include <stdlib.h>
#include <strings.h>
#include <string>
#include <logger.h>
#include <iostream>
#include <omf.h>
#include <piwebapi.h>
#include <ocs.h>
#include <simple_https.h>
#include <simple_http.h>
#include <config_category.h>
#include "rapidjson/writer.h"
#include "rapidjson/stringbuffer.h"
#include "json_utils.h"
#include "libcurl_https.h"
#include "utils.h"
#include "string_utils.h"
#include <version.h>
#include <omfinfo.h>

#include "crypto.hpp"


#define VERBOSE_LOG	0
#define INSTRUMENT 0

using namespace std;
using namespace rapidjson;
using namespace SimpleWeb;
/*
 * Note that the properties "group" is used to group related items, these will appear in different tabs,
 * using the group name, in the GUI.
 *
 * This GUI functionality has yet to be implemented.
 *
 * Current groups used are
 *	"Authentication"	Items relating to authentication with the endpoint
 *	"Connection"		Connection tuning items
 *	"Formats & Types"	Controls for the way formats and types are defined
 *	"Asset Framework"	Asset framework configuration items
 *	"Cloud"			Things related to OCS or ADH only
 *	"Advanced"		Adds to the Advanced tab that already exists
 */
const char *PLUGIN_DEFAULT_CONFIG_INFO = QUOTE(
	{
		"plugin": {
			"description": "PI Server North C Plugin",
			"type": "string",
			"default": PLUGIN_NAME,
			"readonly": "true"
		},
		"PIServerEndpoint": {
			"description": "Select the endpoint among PI Web API, Connector Relay, OSIsoft Cloud Services or Edge Data Store",
			"type": "enumeration",
			"options":["PI Web API", "AVEVA Data Hub", "Connector Relay", "OSIsoft Cloud Services", "Edge Data Store"],
			"default": "PI Web API",
			"order": "1",
			"displayName": "Endpoint"
		},
		"ADHRegions": {
			"description": "AVEVA Data Hub or OSIsoft Cloud Services region",
			"type": "enumeration",
			"options":["US-West", "EU-West", "Australia"],
			"default": "US-West",
			"order": "2",
			"group" : "Cloud",
			"displayName": "Cloud Service Region",
			"validity" : "PIServerEndpoint == \"AVEVA Data Hub\" || PIServerEndpoint == \"OSIsoft Cloud Services\""
		},
		"SendFullStructure": {
			"description": "If true, create an AF structure to organize the data. If false, create PI Points only.",
			"type": "boolean",
			"default": "true",
			"order": "3",
			"displayName": "Create AF structure",
			"validity" : "PIServerEndpoint == \"PI Web API\""
		},
		"NamingScheme": {
			"description": "Define the naming scheme of the objects in the endpoint",
			"type": "enumeration",
			"options":["Concise", "Use Type Suffix", "Use Attribute Hash", "Backward compatibility"],
			"default": "Concise",
			"order": "4",
			"displayName": "Naming Scheme"
		},
		"ServerHostname": {
			"description": "Hostname of the server running the endpoint either PI Web API or Connector Relay",
			"type": "string",
			"default": "localhost",
			"order": "5",
			"displayName": "Server hostname",
			"validity" : "PIServerEndpoint != \"Edge Data Store\" && PIServerEndpoint != \"OSIsoft Cloud Services\" && PIServerEndpoint != \"AVEVA Data Hub\""
		},
		"ServerPort": {
			"description": "Port on which the endpoint either PI Web API or Connector Relay or Edge Data Store is listening, 0 will use the default one",
			"type": "integer",
			"default": "0",
			"order": "6",
			"displayName": "Server port, 0=use the default",
			"validity" : "PIServerEndpoint != \"OSIsoft Cloud Services\" && PIServerEndpoint != \"AVEVA Data Hub\""
		},
		"producerToken": {
			"description": "The producer token that represents this Fledge stream",
			"type": "string",
			"default": "omf_north_0001",
			"order": "7",
			"displayName": "Producer Token",
			"group" : "Authentication",
			"validity" : "PIServerEndpoint == \"Connector Relay\""
		},
		"source": {
			"description": "Defines the source of the data to be sent on the stream, this may be one of either readings, statistics or audit.",
			"type": "enumeration",
			"options":["readings", "statistics"],
			"default": "readings",
			"order": "8",
			"displayName": "Data Source"
		},
		"StaticData": {
			"description": "Static data to include in each sensor reading sent to the PI Server.",
			"type": "string",
			"default": "Location: Palo Alto, Company: Dianomic",
			"order": "9",
			"displayName": "Static Data"
		},
		"AssetDatapointNameDelimiter": {
			"description": "Delimiter character between Asset and Datapoint in PI data stream names",
			"type": "string",
			"default": ".",
			"order": "10",
			"displayName": "Data Stream Name Delimiter"
		},
		"OMFRetrySleepTime": {
			"description": "Seconds between each retry for the communication with the OMF PI Connector Relay, NOTE : the time is doubled at each attempt.",
			"type": "integer",
			"default": "1",
			"order": "11",
			"group": "Connection",
			"displayName": "Sleep Time Retry"
		},
		"OMFMaxRetry": {
			"description": "Max number of retries for the communication with the OMF PI Connector Relay",
			"type": "integer",
			"default": "3",
			"order": "12",
			"group": "Connection",
			"displayName": "Maximum Retry"
		},
		"OMFHttpTimeout": {
			"description": "Timeout in seconds for the HTTP operations with the OMF PI Connector Relay",
			"type": "integer",
			"default": "10",
			"order": "13",
			"group": "Connection",
			"displayName": "HTTP Timeout"
		},
		"formatInteger": {
			"description": "OMF format property to apply to the type Integer",
			"type": "enumeration",
			"default": "int64",
			"options": ["int64", "int32", "int16", "uint64", "uint32", "uint16"],
			"order": "14",
			"group": "Formats & Types",
			"displayName": "Integer Format"
		},
		"formatNumber": {
			"description": "OMF format property to apply to the type Number",
			"type": "enumeration",
			"default": "float64",
			"options": ["float64", "float32"],
			"order": "15",
			"group": "Formats & Types",
			"displayName": "Number Format"
		},
		"compression": {
			"description": "Compress readings data before sending to PI server",
			"type": "boolean",
			"default": "true",
			"order": "16",
			"group": "Connection",
			"displayName": "Compression"
		},
		"DefaultAFLocation": {
			"description": "Defines the default location in the Asset Framework hierarchy in which the assets will be created, each level is separated by /, PI Web API only.",
			"type": "string",
			"default": "/fledge/data_piwebapi/default",
			"order": "17",
			"displayName": "Default Asset Framework Location",
			"group" : "Asset Framework",
			"validity" : "PIServerEndpoint == \"PI Web API\""
		},
		"AFMap": {
			"description": "Defines a set of rules to address where assets should be placed in the AF hierarchy.",
			"type": "JSON",
			"default": AF_HIERARCHY_RULES,
			"order": "18",
			"group" : "Asset Framework",
			"displayName": "Asset Framework hierarchy rules",
			"validity" : "PIServerEndpoint == \"PI Web API\""


		},
		"notBlockingErrors": {
			"description": "These errors are considered not blocking in the communication with the PI Server, the sending operation will proceed with the next block of data if one of these is encountered",
			"type": "JSON",
			"default": NOT_BLOCKING_ERRORS_DEFAULT,
			"order": "19" ,
			"readonly": "true"
		},
		"streamId": {
			"description": "Identifies the specific stream to handle and the related information, among them the ID of the last object streamed.",
			"type": "integer",
			"default": "0",
			"order": "20" ,
			"readonly": "true"
		},
		"PIWebAPIAuthenticationMethod": {
			"description": "Defines the authentication method to be used with the PI Web API.",
			"type": "enumeration",
			"options":["anonymous", "basic", "kerberos"],
			"default": "anonymous",
			"order": "21",
			"group": "Authentication",
			"displayName": "PI Web API Authentication Method",
			"validity" : "PIServerEndpoint == \"PI Web API\""
		},
		"PIWebAPIUserId": {
			"description": "User id of PI Web API to be used with the basic access authentication.",
			"type": "string",
			"default": "user_id",
			"order": "22",
			"group": "Authentication",
			"displayName": "PI Web API User Id",
			"validity" : "PIServerEndpoint == \"PI Web API\" && PIWebAPIAuthenticationMethod == \"basic\""
		},
		"PIWebAPIPassword": {
			"description": "Password of the user of PI Web API to be used with the basic access authentication.",
			"type": "password",
			"default": "password",
			"order": "23" ,
			"group": "Authentication",
			"displayName": "PI Web API Password",
			"validity" : "PIServerEndpoint == \"PI Web API\" && PIWebAPIAuthenticationMethod == \"basic\""
		},
		"PIWebAPIKerberosKeytabFileName": {
			"description": "Keytab file name used for Kerberos authentication in PI Web API.",
			"type": "string",
			"default": "piwebapi_kerberos_https.keytab",
			"order": "24" ,
			"group": "Authentication",
			"displayName": "PI Web API Kerberos keytab file",
			"validity" : "PIServerEndpoint == \"PI Web API\" && PIWebAPIAuthenticationMethod == \"kerberos\""
		},
		"OCSNamespace" : {
			"description" : "Specifies the namespace where the information are stored and it is used for the interaction with AVEVA Data Hub or OCS",
			"type" : "string",
			"default": "name_space",
			"order": "25",
			"group" : "Cloud",
			"displayName" : "Namespace",
			"validity" : "PIServerEndpoint == \"OSIsoft Cloud Services\" || PIServerEndpoint == \"AVEVA Data Hub\""
		},
		"OCSTenantId" : {
			"description" : "Tenant id associated to the specific AVEVA Data Hub or OCS account",
			"type" : "string",
			"default": "ocs_tenant_id",
			"order": "26",
			"group" : "Cloud",
			"displayName" : "Tenant ID",
			"validity" : "PIServerEndpoint == \"OSIsoft Cloud Services\" || PIServerEndpoint == \"AVEVA Data Hub\""
		},
		"OCSClientId" : {
			"description" : "Client id associated to the specific account, it is used to authenticate when using the AVEVA Data Hub or OCS",
			"type" : "string",
			"default": "ocs_client_id",
			"order": "27",
			"group" : "Cloud",
			"displayName" : "Client ID",
			"validity" : "PIServerEndpoint == \"OSIsoft Cloud Services\" || PIServerEndpoint == \"AVEVA Data Hub\""
		},
		"OCSClientSecret" : {
			"description" : "Client secret associated to the specific account, it is used to authenticate with AVEVA Data Hub or OCS",
			"type" : "password",
			"default": "ocs_client_secret",
			"order": "28",
			"group" : "Cloud",
			"displayName" : "Client Secret",
			"validity" : "PIServerEndpoint == \"OSIsoft Cloud Services\" || PIServerEndpoint == \"AVEVA Data Hub\""
		},
		"PIWebAPInotBlockingErrors": {
			"description": "These errors are considered not blocking in the communication with the PI Web API, the sending operation will proceed with the next block of data if one of these is encountered",
			"type": "JSON",
			"default": NOT_BLOCKING_ERRORS_DEFAULT_PI_WEB_API,
			"order": "29" ,
			"readonly": "true"
		},
		"Legacy": {
			"description": "Force all data to be sent using complex OMF types",
			"type": "boolean",
			"default": "false",
			"order": "30",
			"group": "Formats & Types",
			"displayName": "Complex Types"
		}
	}
);

// "default": "{\"pipeline\": [\"DeltaFilter\"]}"


/**
 * Return the information about this plugin
 */
/**
 * The PI Server plugin interface
 */
extern "C" {

/**
 * The C API plugin information structure
 */
static PLUGIN_INFORMATION info = {
	PLUGIN_NAME,			   // Name
	VERSION,			   // Version
	SP_PERSIST_DATA | SP_BUILTIN,	   // Flags
	PLUGIN_TYPE_NORTH,		   // Type
	"1.0.0",			   // Interface version
	PLUGIN_DEFAULT_CONFIG_INFO	   // Configuration
};

/**
 * Return the information about this plugin
 */
PLUGIN_INFORMATION *plugin_info()
{
	return &info;
}

/**
 * Initialise the plugin with configuration.
 *
 * This function is called to get the plugin handle.
 */
PLUGIN_HANDLE plugin_init(ConfigCategory* configData)
{
#if INSTRUMENT
	struct timeval startTime;
	gettimeofday(&startTime, NULL);
#endif

	int endpointPort = 0;

	/**
	 * Handle the PI Server parameters here
	 */
	// Allocate connector struct
	OMFInformation *info = new OMFInformation(configData);
#if INSTRUMENT
	Logger::getLogger()->debug("plugin_init elapsed time: %6.3f seconds", GetElapsedTime(&startTime));
#endif

	return (PLUGIN_HANDLE)info;
}


/**
 * Plugin start with stored plugin_data
 *
 * @param handle	The plugin handle
 * @param storedData	The stored plugin_data
 */
void plugin_start(const PLUGIN_HANDLE handle,
		  const string& storedData)
{
#if INSTRUMENT
	struct timeval startTime;
	gettimeofday(&startTime, NULL);

	// For debugging: write plugin's stored data to a file
	string jsonFilePath = getDataDir() + string("/logs/OMFStoredData.json");
	ofstream f(jsonFilePath.c_str(), ios_base::trunc);
	f << storedData.c_str();
	f.close();
#endif

	Logger* logger = Logger::getLogger();
	OMFInformation *info = (OMFInformation *)handle;
	info->start(storedData);


#if INSTRUMENT
	Logger::getLogger()->debug("plugin_start elapsed time: %6.3f seconds", GetElapsedTime(&startTime));
#endif
}

/**
 * Send Readings data to historian server
 */
uint32_t plugin_send(const PLUGIN_HANDLE handle,
		     const vector<Reading *>& readings)
{
	OMFInformation *info = (OMFInformation *)handle;
	return info->send(readings);
}

/**
 * Shutdown the plugin
 *
 * Delete allocated data
 *
 * Note: the entry with FAKE_ASSET_KEY ios never saved.
 *
 * @param handle   The plugin handle
 * @return         A string with JSON plugin data
 *                 the caller will persist
 */
string plugin_shutdown(PLUGIN_HANDLE handle)
{
	// Delete the handle
	OMFInformation *info = (OMFInformation *) handle;

	string rval = info->saveData();
	delete info;
	return rval;
}

// End of extern "C"
};
