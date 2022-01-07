/*
 * Fledge PI Server north plugin.
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Massimiliano Pinto, Stefano Simonelli
 */
#include <unistd.h>

#include <plugin_api.h>
#include <stdio.h>
#include <stdlib.h>
#include <strings.h>
#include <string>
#include <logger.h>
#include <plugin_exception.h>
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


#include "crypto.hpp"


#define VERBOSE_LOG	0

using namespace std;
using namespace rapidjson;
using namespace SimpleWeb;

#define PLUGIN_NAME "OMF"
#define TYPE_ID_KEY "type-id"
#define SENT_TYPES_KEY "sentDataTypes"
#define DATA_KEY "dataTypes"
#define DATA_KEY_SHORT "dataTypesShort"
#define DATA_KEY_HINT "hintChecksum"
#define NAMING_SCHEME "namingScheme"
#define AFH_HASH "afhHash"
#define AF_HIERARCHY "afHierarchy"
#define AF_HIERARCHY_ORIG "afHierarchyOrig"


#define PROPERTY_TYPE   "type"
#define PROPERTY_NUMBER "number"
#define PROPERTY_STRING "string"


#define ENDPOINT_URL_PI_WEB_API "https://HOST_PLACEHOLDER:PORT_PLACEHOLDER/piwebapi/omf"
#define ENDPOINT_URL_CR         "https://HOST_PLACEHOLDER:PORT_PLACEHOLDER/ingress/messages"
#define ENDPOINT_URL_OCS        "https://dat-b.osisoft.com:PORT_PLACEHOLDER/api/v1/tenants/TENANT_ID_PLACEHOLDER/Namespaces/NAMESPACE_ID_PLACEHOLDER/omf"
#define ENDPOINT_URL_EDS        "http://localhost:PORT_PLACEHOLDER/api/v1/tenants/default/namespaces/default/omf"

enum OMF_ENDPOINT_PORT {
	ENDPOINT_PORT_PIWEB_API=443,
	ENDPOINT_PORT_POINT_CR=5460,
	ENDPOINT_PORT_POINT_OCS=443,
	ENDPOINT_PORT_POINT_EDS=5590
};

/**
 * Plugin specific default configuration
 */

#define NOT_BLOCKING_ERRORS_DEFAULT QUOTE(                              \
	{                                                                   \
		"errors400" : [                                                 \
			"Redefinition of the type with the same ID is not allowed", \
			"Invalid value type for the property",                      \
			"Property does not exist in the type definition",           \
			"Container is not defined",                                 \
			"Unable to find the property of the container of type"      \
		]					                                            \
	}                                                                   \
)

#define NOT_BLOCKING_ERRORS_DEFAULT_PI_WEB_API QUOTE(            \
	{                                                            \
		"EventInfo" : [                                          \
			"The specified value is outside the allowable range" \
		]					                                     \
	}                                                            \
)

#define AF_HIERARCHY_RULES QUOTE(                                          \
	{                                                                     \
	}                                                                     \
)

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
			"options":["PI Web API", "Connector Relay", "OSIsoft Cloud Services", "Edge Data Store"],
			"default": "PI Web API",
			"order": "1",
			"displayName": "Endpoint"
		},
		"SendFullStructure": {
			"description": "It sends the minimum OMF structural messages to load data into Data Archive if disabled",
			"type": "boolean",
			"default": "true",
			"order": "2",
			"displayName": "Send full structure",
			"validity" : "PIServerEndpoint == \"PI Web API\""
		},
		"NamingScheme": {
			"description": "Define the naming scheme of the objects in the endpoint",
			"type": "enumeration",
			"options":["Concise", "Use Type Suffix", "Use Attribute Hash", "Backward compatibility"],
			"default": "Concise",
			"order": "3",
			"displayName": "Naming Scheme"
		},
		"ServerHostname": {
			"description": "Hostname of the server running the endpoint either PI Web API or Connector Relay",
			"type": "string",
			"default": "localhost",
			"order": "4",
			"displayName": "Server hostname",
			"validity" : "PIServerEndpoint != \"Edge Data Store\" && PIServerEndpoint != \"OSIsoft Cloud Services\""
		},
		"ServerPort": {
			"description": "Port on which the endpoint either PI Web API or Connector Relay or Edge Data Store is listening, 0 will use the default one",
			"type": "integer",
			"default": "0",
			"order": "5",
			"displayName": "Server port, 0=use the default",
			"validity" : "PIServerEndpoint != \"OSIsoft Cloud Services\""
		},
		"producerToken": {
			"description": "The producer token that represents this Fledge stream",
			"type": "string",
			"default": "omf_north_0001",
			"order": "6",
			"displayName": "Producer Token",
			"validity" : "PIServerEndpoint == \"Connector Relay\""
		},
		"source": {
			"description": "Defines the source of the data to be sent on the stream, this may be one of either readings, statistics or audit.",
			"type": "enumeration",
			"options":["readings", "statistics"],
			"default": "readings",
			"order": "7",
			"displayName": "Data Source"
		},
		"StaticData": {
			"description": "Static data to include in each sensor reading sent to the PI Server.",
			"type": "string",
			"default": "Location: Palo Alto, Company: Dianomic",
			"order": "8",
			"displayName": "Static Data"
		},
		"OMFRetrySleepTime": {
			"description": "Seconds between each retry for the communication with the OMF PI Connector Relay, NOTE : the time is doubled at each attempt.",
			"type": "integer",
			"default": "1",
			"order": "9",
			"displayName": "Sleep Time Retry"
		},
		"OMFMaxRetry": {
			"description": "Max number of retries for the communication with the OMF PI Connector Relay",
			"type": "integer",
			"default": "3",
			"order": "10",
			"displayName": "Maximum Retry"
		},
		"OMFHttpTimeout": {
			"description": "Timeout in seconds for the HTTP operations with the OMF PI Connector Relay",
			"type": "integer",
			"default": "10",
			"order": "11",
			"displayName": "HTTP Timeout"
		},
		"formatInteger": {
			"description": "OMF format property to apply to the type Integer",
			"type": "string",
			"default": "int64",
			"order": "12",
			"displayName": "Integer Format"
		},
		"formatNumber": {
			"description": "OMF format property to apply to the type Number",
			"type": "string",
			"default": "float64",
			"order": "13",
			"displayName": "Number Format"
		},
		"compression": {
			"description": "Compress readings data before sending to PI server",
			"type": "boolean",
			"default": "true",
			"order": "14",
			"displayName": "Compression"
		},
		"DefaultAFLocation": {
			"description": "Defines the default location in the Asset Framework hierarchy in which the assets will be created, each level is separated by /, PI Web API only.",
			"type": "string",
			"default": "/fledge/data_piwebapi/default",
			"order": "15",
			"displayName": "Default Asset Framework Location",
			"validity" : "PIServerEndpoint == \"PI Web API\""
		},
		"AFMap": {
			"description": "Defines a set of rules to address where assets should be placed in the AF hierarchy.",
			"type": "JSON",
			"default": AF_HIERARCHY_RULES,
			"order": "16",
			"displayName": "Asset Framework hierarchy rules",
			"validity" : "PIServerEndpoint == \"PI Web API\""


		},
		"notBlockingErrors": {
			"description": "These errors are considered not blocking in the communication with the PI Server, the sending operation will proceed with the next block of data if one of these is encountered",
			"type": "JSON",
			"default": NOT_BLOCKING_ERRORS_DEFAULT,
			"order": "17" ,
			"readonly": "true"
		},
		"streamId": {
			"description": "Identifies the specific stream to handle and the related information, among them the ID of the last object streamed.",
			"type": "integer",
			"default": "0",
			"order": "18" ,
			"readonly": "true"
		},
		"PIWebAPIAuthenticationMethod": {
			"description": "Defines the authentication method to be used with the PI Web API.",
			"type": "enumeration",
			"options":["anonymous", "basic", "kerberos"],
			"default": "anonymous",
			"order": "19",
			"displayName": "PI Web API Authentication Method",
			"validity" : "PIServerEndpoint == \"PI Web API\""
		},
		"PIWebAPIUserId": {
			"description": "User id of PI Web API to be used with the basic access authentication.",
			"type": "string",
			"default": "user_id",
			"order": "20",
			"displayName": "PI Web API User Id",
			"validity" : "PIServerEndpoint == \"PI Web API\" && PIWebAPIAuthenticationMethod == \"basic\""
		},
		"PIWebAPIPassword": {
			"description": "Password of the user of PI Web API to be used with the basic access authentication.",
			"type": "password",
			"default": "password",
			"order": "21" ,
			"displayName": "PI Web API Password",
			"validity" : "PIServerEndpoint == \"PI Web API\" && PIWebAPIAuthenticationMethod == \"basic\""
		},
		"PIWebAPIKerberosKeytabFileName": {
			"description": "Keytab file name used for Kerberos authentication in PI Web API.",
			"type": "string",
			"default": "piwebapi_kerberos_https.keytab",
			"order": "22" ,
			"displayName": "PI Web API Kerberos keytab file",
			"validity" : "PIServerEndpoint == \"PI Web API\" && PIWebAPIAuthenticationMethod == \"kerberos\""
		},
		"OCSNamespace" : {
			"description" : "Specifies the OCS namespace where the information are stored and it is used for the interaction with the OCS API",
			"type" : "string",
			"default": "name_space",
			"order": "23",
			"displayName" : "OCS Namespace",
			"validity" : "PIServerEndpoint == \"OSIsoft Cloud Services\""
		},
		"OCSTenantId" : {
			"description" : "Tenant id associated to the specific OCS account",
			"type" : "string",
			"default": "ocs_tenant_id",
			"order": "24",
			"displayName" : "OCS Tenant ID",
			"validity" : "PIServerEndpoint == \"OSIsoft Cloud Services\""
		},
		"OCSClientId" : {
			"description" : "Client id associated to the specific OCS account, it is used to authenticate the source for using the OCS API",
			"type" : "string",
			"default": "ocs_client_id",
			"order": "25",
			"displayName" : "OCS Client ID",
			"validity" : "PIServerEndpoint == \"OSIsoft Cloud Services\""
		},
		"OCSClientSecret" : {
			"description" : "Client secret associated to the specific OCS account, it is used to authenticate the source for using the OCS API",
			"type" : "password",
			"default": "ocs_client_secret",
			"order": "26",
			"displayName" : "OCS Client Secret",
			"validity" : "PIServerEndpoint == \"OSIsoft Cloud Services\""
		},
		"PIWebAPInotBlockingErrors": {
			"description": "These errors are considered not blocking in the communication with the PI Web API, the sending operation will proceed with the next block of data if one of these is encountered",
			"type": "JSON",
			"default": NOT_BLOCKING_ERRORS_DEFAULT_PI_WEB_API,
			"order": "27" ,
			"readonly": "true"
		}
	}
);

// "default": "{\"pipeline\": [\"DeltaFilter\"]}"

/**
 * Historian PI Server connector info
 */
typedef struct
{
	HttpSender	*sender;                // HTTPS connection
	OMF 		*omf;                   // OMF data protocol
	bool        sendFullStructure;      // It sends the minimum OMF structural messages to load data into Data Archive if disabled
	bool		compression;            // whether to compress readings' data
	string		protocol;               // http / https
	string		hostAndPort;            // hostname:port for SimpleHttps
	unsigned int	retrySleepTime;     // Seconds between each retry
	unsigned int	maxRetry;	        // Max number of retries in the communication
	unsigned int	timeout;	        // connect and operation timeout
	string		path;		            // PI Server application path
	long		typeId;		            // OMF protocol type-id prefix
	string		producerToken;	        // PI Server connector token
	string		formatNumber;	        // OMF protocol Number format
	string		formatInteger;	        // OMF protocol Integer format
	OMF_ENDPOINT PIServerEndpoint;      // Defines which End point should be used for the communication
	NAMINGSCHEME_ENDPOINT NamingScheme; // Define how the object names should generated
	string		DefaultAFLocation;      // 1st hierarchy in Asset Framework, PI Web API only.
	string		AFMap;                  // Defines a set of rules to address where assets should be placed in the AF hierarchy.

	string		prefixAFAsset;          // Prefix to generate unique asste id
	string		PIWebAPIProductTitle;
	string		PIWebAPIVersion;
	string		PIWebAPIAuthMethod;     // Authentication method to be used with the PI Web API.
	string		PIWebAPICredentials;    // Credentials is the base64 encoding of id and password joined by a single colon (:)
	string 		KerberosKeytab;         // Kerberos authentication keytab file
	                                    //   stores the environment variable value about the keytab file path
	                                    //   to allow the environment to persist for all the execution of the plugin
	                                    //
	                                    //   Note : A keytab is a file containing pairs of Kerberos principals
	                                    //   and encrypted keys (which are derived from the Kerberos password).
	                                    //   You can use a keytab file to authenticate to various remote systems
	                                    //   using Kerberos without entering a password.

	string		OCSNamespace;           // OCS configurations
	string		OCSTenantId;
	string		OCSClientId;
	string		OCSClientSecret;
	string		OCSToken;

	vector<pair<string, string>>
			staticData;	// Static data
        // Errors considered not blocking in the communication with the PI Server
	std::vector<std::string>
			notBlockingErrors;
	// Per asset DataTypes
	std::map<std::string, OMFDataTypes>
			assetsDataTypes;
} CONNECTOR_INFO;

unsigned long calcTypeShort                (const string& dataTypes);
string        saveSentDataTypes            (CONNECTOR_INFO* connInfo);
void          loadSentDataTypes            (CONNECTOR_INFO* connInfo, Document& JSONData);
long          getMaxTypeId                 (CONNECTOR_INFO* connInfo);
OMF_ENDPOINT  identifyPIServerEndpoint     (CONNECTOR_INFO* connInfo);
string        AuthBasicCredentialsGenerate (string& userId, string& password);
void          AuthKerberosSetup            (string& keytabFile, string& keytabFileName);
string        OCSRetrieveAuthToken         (CONNECTOR_INFO* connInfo);
string        PIWebAPIGetVersion           (CONNECTOR_INFO* connInfo);

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
	int endpointPort = 0;

	/**
	 * Handle the PI Server parameters here
	 */
	// Allocate connector struct
	CONNECTOR_INFO *connInfo = new CONNECTOR_INFO;

	// PIServerEndpoint handling
	string PIServerEndpoint = configData->getValue("PIServerEndpoint");
	string ServerHostname = configData->getValue("ServerHostname");
	string ServerPort = configData->getValue("ServerPort");
	string url;
	string NamingScheme = configData->getValue("NamingScheme");
	{
		// Translate the PIServerEndpoint configuration
		if(PIServerEndpoint.compare("PI Web API") == 0)
		{
			Logger::getLogger()->debug("PI-Server end point manually selected - PI Web API ");
			connInfo->PIServerEndpoint = ENDPOINT_PIWEB_API;
			url                        = ENDPOINT_URL_PI_WEB_API;
			endpointPort               = ENDPOINT_PORT_PIWEB_API;
		}
		else if(PIServerEndpoint.compare("Connector Relay") == 0)
		{
			Logger::getLogger()->debug("PI-Server end point manually selected - Connector Relay ");
			connInfo->PIServerEndpoint = ENDPOINT_CR;
			url                        = ENDPOINT_URL_CR;
			endpointPort               = ENDPOINT_PORT_POINT_CR;
		}
		else if(PIServerEndpoint.compare("OSIsoft Cloud Services") == 0)
		{
			Logger::getLogger()->debug("End point manually selected - OSIsoft Cloud Services");
			connInfo->PIServerEndpoint = ENDPOINT_OCS;
			url                        = ENDPOINT_URL_OCS;
			endpointPort               = ENDPOINT_PORT_POINT_OCS;
		}
		else if(PIServerEndpoint.compare("Edge Data Store") == 0)
		{
			Logger::getLogger()->debug("End point manually selected - OSIsoft Cloud Services");
			connInfo->PIServerEndpoint = ENDPOINT_EDS;
			url                        = ENDPOINT_URL_EDS;
			endpointPort               = ENDPOINT_PORT_POINT_EDS;
		}
		ServerPort = (ServerPort.compare("0") == 0) ? to_string(endpointPort) : ServerPort;
	}

	if (endpointPort == ENDPOINT_PORT_PIWEB_API) {

		// Use SendFullStructure ?
		string fullStr = configData->getValue("SendFullStructure");

		if (fullStr == "True" || fullStr == "true" || fullStr == "TRUE")
			connInfo->sendFullStructure = true;
		else
			connInfo->sendFullStructure = false;
	} else {
		connInfo->sendFullStructure = true;
	}

	unsigned int retrySleepTime = atoi(configData->getValue("OMFRetrySleepTime").c_str());
	unsigned int maxRetry = atoi(configData->getValue("OMFMaxRetry").c_str());
	unsigned int timeout = atoi(configData->getValue("OMFHttpTimeout").c_str());

	string producerToken = configData->getValue("producerToken");

	string formatNumber = configData->getValue("formatNumber");
	string formatInteger = configData->getValue("formatInteger");
	string DefaultAFLocation = configData->getValue("DefaultAFLocation");
	string AFMap = configData->getValue("AFMap");

	string PIWebAPIAuthMethod     = configData->getValue("PIWebAPIAuthenticationMethod");
	string PIWebAPIUserId         = configData->getValue("PIWebAPIUserId");
	string PIWebAPIPassword       = configData->getValue("PIWebAPIPassword");
	string KerberosKeytabFileName = configData->getValue("PIWebAPIKerberosKeytabFileName");

	// OCS configurations
	string OCSNamespace    = configData->getValue("OCSNamespace");
	string OCSTenantId     = configData->getValue("OCSTenantId");
	string OCSClientId     = configData->getValue("OCSClientId");
	string OCSClientSecret = configData->getValue("OCSClientSecret");

	StringReplace(url, "HOST_PLACEHOLDER", ServerHostname);
	StringReplace(url, "PORT_PLACEHOLDER", ServerPort);

	// TENANT_ID_PLACEHOLDER and NAMESPACE_ID_PLACEHOLDER, if present, will be replaced with the values of OCSTenantId and OCSNamespace
	StringReplace(url, "TENANT_ID_PLACEHOLDER",    OCSTenantId);
	StringReplace(url, "NAMESPACE_ID_PLACEHOLDER", OCSNamespace);

	/**
	 * Extract host, port, path from URL
	 */
	size_t findProtocol = url.find_first_of(":");
	string protocol = url.substr(0, findProtocol);

	string tmpUrl = url.substr(findProtocol + 3);
	size_t findPort = tmpUrl.find_first_of(":");
	string hostName = tmpUrl.substr(0, findPort);

	size_t findPath = tmpUrl.find_first_of("/");
	string port = tmpUrl.substr(findPort + 1, findPath - findPort - 1);
	string path = tmpUrl.substr(findPath);

	string hostAndPort(hostName + ":" + port);

	// Set configuration fields
	connInfo->protocol = protocol;
	connInfo->hostAndPort = hostAndPort;
	connInfo->path = path;
	connInfo->retrySleepTime = retrySleepTime;
	connInfo->maxRetry = maxRetry;
	connInfo->timeout = timeout;
	connInfo->typeId = TYPE_ID_DEFAULT;
	connInfo->producerToken = producerToken;
	connInfo->formatNumber = formatNumber;
	connInfo->formatInteger = formatInteger;
	connInfo->DefaultAFLocation = DefaultAFLocation;
	connInfo->AFMap = AFMap;

	// OCS configurations
	connInfo->OCSNamespace    = OCSNamespace;
	connInfo->OCSTenantId     = OCSTenantId;
	connInfo->OCSClientId     = OCSClientId;
	connInfo->OCSClientSecret = OCSClientSecret;

	// PI Web API end-point - evaluates the authentication method requested
	if (PIWebAPIAuthMethod.compare("anonymous") == 0)
	{
		Logger::getLogger()->debug("PI Web API end-point - anonymous authentication");
		connInfo->PIWebAPIAuthMethod = "a";
	}
	else if (PIWebAPIAuthMethod.compare("basic") == 0)
	{
		Logger::getLogger()->debug("PI Web API end-point - basic authentication");
		connInfo->PIWebAPIAuthMethod = "b";
		connInfo->PIWebAPICredentials = AuthBasicCredentialsGenerate(PIWebAPIUserId, PIWebAPIPassword);
	}
	else if (PIWebAPIAuthMethod.compare("kerberos") == 0)
	{
		Logger::getLogger()->debug("PI Web API end-point - kerberos authentication");
		connInfo->PIWebAPIAuthMethod = "k";
		AuthKerberosSetup(connInfo->KerberosKeytab, KerberosKeytabFileName);
	}
	else
	{
		Logger::getLogger()->error("Invalid authentication method for PI Web API :%s: ", PIWebAPIAuthMethod.c_str());
	}

	// Use compression ?
	string compr = configData->getValue("compression");
	if (compr == "True" || compr == "true" || compr == "TRUE")
		connInfo->compression = true;
	else
		connInfo->compression = false;

	// Set the list of errors considered not blocking in the communication
	// with the PI Server
	if (connInfo->PIServerEndpoint == ENDPOINT_PIWEB_API)
	{
		JSONStringToVectorString(connInfo->notBlockingErrors ,
								 configData->getValue("PIWebAPInotBlockingErrors"),
								 std::string("EventInfo"));
	}
	else
	{
		JSONStringToVectorString(connInfo->notBlockingErrors ,
								 configData->getValue("notBlockingErrors"),
								 std::string("errors400"));
	}
	/**
	 * Add static data
	 * Split the string up into each pair
	 */
	string staticData = configData->getValue("StaticData");
	size_t pos = 0;
	size_t start = 0;
	do {
		pos = staticData.find(",", start);
		string item = staticData.substr(start, pos);
		start = pos + 1;
		size_t pos2 = 0;
		if ((pos2 = item.find(":")) != string::npos)
		{
			string name = item.substr(0, pos2);
			while (name[0] == ' ')
				name = name.substr(1);
			string value = item.substr(pos2 + 1);
			while (value[0] == ' ')
				value = value.substr(1);
			pair<string, string> sData = make_pair(name, value);
			connInfo->staticData.push_back(sData);
		}
	} while (pos != string::npos);

	{
		// NamingScheme handling
		if(NamingScheme.compare("Concise") == 0)
		{
			connInfo->NamingScheme = NAMINGSCHEME_CONCISE;
		}
		else if(NamingScheme.compare("Use Type Suffix") == 0)
		{
			connInfo->NamingScheme = NAMINGSCHEME_SUFFIX;
		}
		else if(NamingScheme.compare("Use Attribute Hash") == 0)
		{
			connInfo->NamingScheme = NAMINGSCHEME_HASH;
		}
		else if(NamingScheme.compare("Backward compatibility") == 0)
		{
			connInfo->NamingScheme = NAMINGSCHEME_COMPATIBILITY;
		}
		Logger::getLogger()->debug("End point naming scheme :%s: ", NamingScheme.c_str() );

	}

	// retrieves the Pi Web Api Version
	if (connInfo->PIServerEndpoint == ENDPOINT_PIWEB_API)
	{
		connInfo->PIWebAPIVersion = PIWebAPIGetVersion(connInfo);
		Logger::getLogger()->info("PIWebAPI version :%s:" ,connInfo->PIWebAPIVersion.c_str() );
	}

#if VERBOSE_LOG
	// Log plugin configuration
	Logger::getLogger()->info("%s plugin configured: URL=%s, "
				  "producerToken=%s, compression=%s",
				  PLUGIN_NAME,
				  url.c_str(),
				  producerToken.c_str(),
				  connInfo->compression ? "True" : "False");
#endif

	return (PLUGIN_HANDLE)connInfo;
}


/**
 * Plugin start with sored plugin_data
 *
 * @param handle	The plugin handle
 * @param storedData	The stored plugin_data
 */
void plugin_start(const PLUGIN_HANDLE handle,
		  const string& storedData)
{
	Logger* logger = Logger::getLogger();
	CONNECTOR_INFO* connInfo = (CONNECTOR_INFO *)handle;

	// Parse JSON plugin_data
	Document JSONData;
	JSONData.Parse(storedData.c_str());
	if (JSONData.HasParseError())
	{
		logger->error("%s plugin error: failure parsing "
			      "plugin data JSON object '%s'",
			      PLUGIN_NAME,
			      storedData.c_str());
	}
	else if(JSONData.HasMember(TYPE_ID_KEY) &&
		(JSONData[TYPE_ID_KEY].IsString() ||
		 JSONData[TYPE_ID_KEY].IsNumber()))
	{
		// Update type-id in PLUGIN_HANDLE object
		if (JSONData[TYPE_ID_KEY].IsNumber())
		{
			connInfo->typeId = JSONData[TYPE_ID_KEY].GetInt();
		}
		else
		{
			connInfo->typeId = atol(JSONData[TYPE_ID_KEY].GetString());
		}
	}

	// Load sentdataTypes
	loadSentDataTypes(connInfo, JSONData);

	// Log default type-id
	if (connInfo->assetsDataTypes.size() == 1 &&
	    connInfo->assetsDataTypes.find(FAKE_ASSET_KEY) != connInfo->assetsDataTypes.end())
	{
		// Only one value: we have the FAKE_ASSET_KEY and no other data
		Logger::getLogger()->info("%s plugin is using global OMF prefix %s=%d",
					  PLUGIN_NAME,
					  TYPE_ID_KEY,
					  connInfo->typeId);
	}
	else
	{
		Logger::getLogger()->info("%s plugin is using per asset OMF prefix %s=%d "
					  "(max value found)",
					  PLUGIN_NAME,
					  TYPE_ID_KEY,
					  getMaxTypeId(connInfo));
	}
}

/**
 * Send Readings data to historian server
 */
uint32_t plugin_send(const PLUGIN_HANDLE handle,
		     const vector<Reading *>& readings)
{
	CONNECTOR_INFO* connInfo = (CONNECTOR_INFO *)handle;

	/**
	 * Allocate the HTTPS handler for "Hostname : port"
	 * connect_timeout and request_timeout.
	 * Default is no timeout at all
	 */
	if (connInfo->PIWebAPIAuthMethod.compare("k") == 0)
	{
		connInfo->sender = new LibcurlHttps(connInfo->hostAndPort,
						    connInfo->timeout,
						    connInfo->timeout,
						    connInfo->retrySleepTime,
						    connInfo->maxRetry);
	}
	else
	{
		if (connInfo->protocol.compare("http") == 0)
		{
			connInfo->sender = new SimpleHttp(connInfo->hostAndPort,
											  connInfo->timeout,
											  connInfo->timeout,
											  connInfo->retrySleepTime,
											  connInfo->maxRetry);
		}
		else
		{
			connInfo->sender = new SimpleHttps(connInfo->hostAndPort,
											   connInfo->timeout,
											   connInfo->timeout,
											   connInfo->retrySleepTime,
											   connInfo->maxRetry);
		}
	}

	connInfo->sender->setAuthMethod          (connInfo->PIWebAPIAuthMethod);
	connInfo->sender->setAuthBasicCredentials(connInfo->PIWebAPICredentials);

	// OCS configurations
	connInfo->sender->setOCSNamespace        (connInfo->OCSNamespace);
	connInfo->sender->setOCSTenantId         (connInfo->OCSTenantId);
	connInfo->sender->setOCSClientId         (connInfo->OCSClientId);
	connInfo->sender->setOCSClientSecret     (connInfo->OCSClientSecret);

	// OCS - retreievs the authentication token
	if (connInfo->PIServerEndpoint == ENDPOINT_OCS)
	{
		connInfo->OCSToken = OCSRetrieveAuthToken(connInfo);
		connInfo->sender->setOCSToken  (connInfo->OCSToken);
	}

	// Allocate the PI Server data protocol
	connInfo->omf = new OMF(*connInfo->sender,
				connInfo->path,
				connInfo->assetsDataTypes,
				connInfo->producerToken);

	connInfo->omf->setSendFullStructure(connInfo->sendFullStructure);

	// Set PIServerEndpoint configuration
	connInfo->omf->setNamingScheme(connInfo->NamingScheme);
	connInfo->omf->setPIServerEndpoint(connInfo->PIServerEndpoint);
	connInfo->omf->setDefaultAFLocation(connInfo->DefaultAFLocation);
	connInfo->omf->setAFMap(connInfo->AFMap);

	// Generates the prefix to have unique asset_id across different levels of hierarchies
	string AFHierarchyLevel;
	connInfo->omf->generateAFHierarchyPrefixLevel(connInfo->DefaultAFLocation, connInfo->prefixAFAsset, AFHierarchyLevel);

	connInfo->omf->setPrefixAFAsset(connInfo->prefixAFAsset);

	// Set OMF FormatTypes  
	connInfo->omf->setFormatType(OMF_TYPE_FLOAT,
				     connInfo->formatNumber);
	connInfo->omf->setFormatType(OMF_TYPE_INTEGER,
				     connInfo->formatInteger);

	connInfo->omf->setStaticData(&connInfo->staticData);
	connInfo->omf->setNotBlockingErrors(connInfo->notBlockingErrors);

	// Send data
	uint32_t ret = connInfo->omf->sendToServer(readings,
						   connInfo->compression);

	// Detect typeId change in OMF class
	if (connInfo->omf->getTypeId() != connInfo->typeId)
	{
		// Update typeId in plugin handle
		connInfo->typeId = connInfo->omf->getTypeId();
		// Log change
		Logger::getLogger()->info("%s plugin: a new OMF global %s (%d) has been created.",
					  PLUGIN_NAME,
					  TYPE_ID_KEY,
					  connInfo->typeId);
	}
	// Delete objects
	delete connInfo->sender;
	delete connInfo->omf;

	// Return sent data ret code
	return ret;
}

/**
 * Shutdown the plugin
 *
 * Delete allocated data
 *
 * Note: the entry with FAKE_ASSET_KEY ios never saved.
 *
 * @param handle    The plugin handle
 * @return	    A string with JSON plugin data
 *		    the caller will persist
 */
string plugin_shutdown(PLUGIN_HANDLE handle)
{
	// Delete the handle
	CONNECTOR_INFO* connInfo = (CONNECTOR_INFO *) handle;

	// Create save data
	std::ostringstream saveData;
	saveData << "{";

	// Add sent data types
	string typesData = saveSentDataTypes(connInfo);
	if (!typesData.empty())
	{
		// Save datatypes
		saveData << typesData;
	}
	else
	{
		// Just save type-id
		saveData << "\"" << TYPE_ID_KEY << "\": " << to_string(connInfo->typeId);
	}

	saveData << "}";

        // Log saving the plugin configuration
        Logger::getLogger()->debug("%s plugin: saving plugin_data '%s'",
				   PLUGIN_NAME,
				   saveData.str().c_str());

	// Delete plugin handle
	delete connInfo;

	// Return current plugin data to save
	return saveData.str();
}

// End of extern "C"
};

/**
 * Return a JSON string with the dataTypes to save in plugion_data
 *
 * Note: the entry with FAKE_ASSET_KEY is never saved.
 *
 * @param   connInfo	The CONNECTOR_INFO data scructure
 * @return		The string with JSON data
 */
string saveSentDataTypes(CONNECTOR_INFO* connInfo)
{
	string ret;
	std::ostringstream newData;

	auto it = connInfo->assetsDataTypes.find(FAKE_ASSET_KEY);
	if (it != connInfo->assetsDataTypes.end())
	{
		// Set typeId in FAKE_ASSET_KEY
		connInfo->typeId = (*it).second.typeId;
		// Remove the entry
		connInfo->assetsDataTypes.erase(it);
	}


	unsigned long tSize = connInfo->assetsDataTypes.size();
	if (tSize)
	{
		
		// Prepare output data (skip empty data types)
		newData << "\"" << SENT_TYPES_KEY << "\" : [";

		bool pendingSeparator = false;
		for (auto it = connInfo->assetsDataTypes.begin();
			  it != connInfo->assetsDataTypes.end();
			  ++it)
		{
			if (((*it).second).types.compare("{}") != 0)
			{
				newData << (pendingSeparator ? ", " : "");
				newData << "{\"" << (*it).first << "\" : {\"" << TYPE_ID_KEY <<
					   "\": " << to_string(((*it).second).typeId);

				// The information should be stored as string in hexadecimal format
				std::stringstream tmpStream;
				tmpStream << std::hex << ((*it).second).typesShort;
				std::string typesShort = tmpStream.str();

				newData << ", \"" << DATA_KEY_SHORT << "\": \"0x" << typesShort << "\"";
				std::stringstream hintStream;
				hintStream << std::hex << ((*it).second).hintChkSum;
				std::string hintChecksum = hintStream.str();
				newData << ", \"" << DATA_KEY_HINT << "\": \"0x" << hintChecksum << "\"";

				long NamingScheme;
				NamingScheme = ((*it).second).namingScheme;
				newData << ", \"" << NAMING_SCHEME << "\": " << to_string(NamingScheme) << "";

				string AFHHash;
				AFHHash = ((*it).second).afhHash;
				newData << ", \"" << AFH_HASH << "\": \"" << AFHHash << "\"";

				string AFHierarchy;
				AFHierarchy = ((*it).second).afHierarchy;
				newData << ", \"" << AF_HIERARCHY << "\": \"" << AFHierarchy << "\"";

				string AFHierarchyOrig;
				AFHierarchyOrig = ((*it).second).afHierarchyOrig;
				newData << ", \"" << AF_HIERARCHY_ORIG << "\": \"" << AFHierarchyOrig << "\"";

				Logger::getLogger()->debug("%s - AFHHash :%s: AFHierarchy :%s: AFHierarchyOrig :%s:", __FUNCTION__, AFHHash.c_str(), AFHierarchy.c_str(), AFHierarchyOrig.c_str()  );
				Logger::getLogger()->debug("%s - NamingScheme :%ld: ", __FUNCTION__,NamingScheme );

				newData << ", \"" << DATA_KEY << "\": " <<
					   (((*it).second).types.empty() ? "{}" : ((*it).second).types) <<
					   "}}";
				pendingSeparator = true;
			}
		}

		tSize = connInfo->assetsDataTypes.size();
		if (!tSize)
		{
			// DataTypes map is empty
			return ret;
		}

		newData << "]";

		ret = newData.str();
	}

	return ret;
}


/**
 * Calculate the TypeShort in the case it is missing loading type definition
 *
 * Generate a 64 bit number containing  a set of counts,
 * number of datapoint in an asset and the number of datapoint of each type we support.
 *
 */
unsigned long calcTypeShort(const string& dataTypes)
{
	union t_typeCount {
		struct
		{
			unsigned char tTotal;
			unsigned char tFloat;
			unsigned char tString;
			unsigned char spare0;

			unsigned char spare1;
			unsigned char spare2;
			unsigned char spare3;
			unsigned char spare4;
		} cnt;
		unsigned long valueLong = 0;

	} typeCount;

	Document JSONData;
	JSONData.Parse(dataTypes.c_str());

	if (JSONData.HasParseError())
	{
		Logger::getLogger()->error("calcTypeShort - unable to calculate TypeShort on :%s: ", dataTypes.c_str());
		return (0);
	}

	for (Value::ConstMemberIterator it = JSONData.MemberBegin(); it != JSONData.MemberEnd(); ++it)
	{

		string key = it->name.GetString();
		const Value& value = it->value;

		if (value.HasMember(PROPERTY_TYPE) && value[PROPERTY_TYPE].IsString())
		{
			string type =value[PROPERTY_TYPE].GetString();

			// Integer is handled as float in the OMF integration
			if (type.compare(PROPERTY_NUMBER) == 0)
			{
				typeCount.cnt.tFloat++;
			} else if (type.compare(PROPERTY_STRING) == 0)
			{
				typeCount.cnt.tString++;
			} else {

				Logger::getLogger()->error("calcTypeShort - unrecognized type :%s: ", type.c_str());
			}
			typeCount.cnt.tTotal++;
		}
		else
		{
			Logger::getLogger()->error("calcTypeShort - unable to extract the type for :%s: ", key.c_str());
			return (0);
		}
	}

	return typeCount.valueLong;
}


/**
 * Load stored data types (already sent to PI server)
 *
 * Each element, the assetName,  has type-id and datatype for each datapoint
 *
 * If no data exists in the plugin_data table, then a map entry
 * with FAKE_ASSET_KEY is made in order to set the start type-id
 * sequence with default value set to 1:
 * all new created OMF dataTypes have type-id prefix set to the value of 1.
 *
 * If data like {"type-id": 14} or {"type-id": "14" } is found, a map entry
 * with FAKE_ASSET_KEY is made and the start type-id sequence value is set
 * to the found value, i.e. 14:
 * all new created OMF dataTypes have type-id prefix set to the value of 14.
 *
 * If proper per asset types data is loaded, the FAKE_ASSET_KEY is not set:
 * all new created OMF dataTypes have type-id prefix set to the value of 1
 * while existing (loaded) OMF dataTypes will keep their type-id values.
 *
 * @param   connInfo	The CONNECTOR_INFO data structure
 * @param   JSONData	The JSON document containing all saved data
 */
void loadSentDataTypes(CONNECTOR_INFO* connInfo,
                        Document& JSONData)
{
	if (JSONData.HasMember(SENT_TYPES_KEY) &&
	    JSONData[SENT_TYPES_KEY].IsArray())
	{
		const Value& cachedTypes = JSONData[SENT_TYPES_KEY];
		for (Value::ConstValueIterator it = cachedTypes.Begin();
						it != cachedTypes.End();
						++it)
		{
			if (!it->IsObject())
			{
				Logger::getLogger()->warn("%s plugin: current element in '%s' " \
							  "property is not an object, ignoring it",
							  PLUGIN_NAME,
							  SENT_TYPES_KEY);
				continue;
			}

			for (Value::ConstMemberIterator itr = it->MemberBegin();
							itr != it->MemberEnd();
							++itr)
			{
				string key = itr->name.GetString();
				const Value& cachedValue = itr->value;

				// Add typeId and dataTypes to the in memory cache
				long typeId;
				if (cachedValue.HasMember(TYPE_ID_KEY) &&
				    cachedValue[TYPE_ID_KEY].IsNumber())
				{
					typeId = cachedValue[TYPE_ID_KEY].GetInt();
				}
				else
				{
					Logger::getLogger()->warn("%s plugin: current element '%s'" \
								  " doesn't have '%s' property, ignoring it",
								  PLUGIN_NAME,
								  key.c_str(),
								  TYPE_ID_KEY);
					continue;
				}

				long NamingScheme;
				if (cachedValue.HasMember(NAMING_SCHEME) &&
					cachedValue[NAMING_SCHEME].IsNumber())
				{
					NamingScheme = cachedValue[NAMING_SCHEME].GetInt();
				}
				else
				{
					Logger::getLogger()->warn("%s plugin: current element '%s'" \
								  " doesn't have '%s' property, handling naming scheme in compatibility mode",
											  PLUGIN_NAME,
											  key.c_str(),
											  NAMING_SCHEME);
					NamingScheme = NAMINGSCHEME_COMPATIBILITY;
				}

				string AFHHash;
				if (cachedValue.HasMember(AFH_HASH) &&
					cachedValue[AFH_HASH].IsString())
				{
					AFHHash = cachedValue[AFH_HASH].GetString();
				}
				else
				{
					Logger::getLogger()->warn("%s plugin: current element '%s'" \
								  " doesn't have '%s' property",
											  PLUGIN_NAME,
											  key.c_str(),
											  AFH_HASH);
					AFHHash = "";
				}

				string AFHierarchy;
				if (cachedValue.HasMember(AF_HIERARCHY) &&
					cachedValue[AF_HIERARCHY].IsString())
				{
					AFHierarchy = cachedValue[AF_HIERARCHY].GetString();
				}
				else
				{
					Logger::getLogger()->warn("%s plugin: current element '%s'" \
								  " doesn't have '%s' property",
											  PLUGIN_NAME,
											  key.c_str(),
											  AF_HIERARCHY);
					AFHierarchy = "";
				}

				string AFHierarchyOrig;
				if (cachedValue.HasMember(AF_HIERARCHY_ORIG) &&
					cachedValue[AF_HIERARCHY_ORIG].IsString())
				{
					AFHierarchyOrig = cachedValue[AF_HIERARCHY_ORIG].GetString();
				}
				else
				{
					Logger::getLogger()->warn("%s plugin: current element '%s'" \
								  " doesn't have '%s' property",
											  PLUGIN_NAME,
											  key.c_str(),
											  AF_HIERARCHY_ORIG);
					AFHierarchyOrig = "";
				}

				string dataTypes;
				if (cachedValue.HasMember(DATA_KEY) &&
				    cachedValue[DATA_KEY].IsObject())
				{
					StringBuffer buffer;
					Writer<StringBuffer> writer(buffer);
					const Value& types = cachedValue[DATA_KEY];
					types.Accept(writer);
					dataTypes = buffer.GetString();
				}
				else
				{
					Logger::getLogger()->warn("%s plugin: current element '%s'" \
								  " doesn't have '%s' property, ignoring it",
								  PLUGIN_NAME,
								  key.c_str(),
								  DATA_KEY);

					continue;
				}

				unsigned long dataTypesShort;
				if (cachedValue.HasMember(DATA_KEY_SHORT) &&
					cachedValue[DATA_KEY_SHORT].IsString())
				{
					string strDataTypesShort = cachedValue[DATA_KEY_SHORT].GetString();
					// The information are stored as string in hexadecimal format
					dataTypesShort = stoi (strDataTypesShort,nullptr,16);
				}
				else
				{
					dataTypesShort = calcTypeShort(dataTypes);
					if (dataTypesShort == 0)
					{
						Logger::getLogger()->warn("%s plugin: current element '%s'" \
                                      " doesn't have '%s' property",
												  PLUGIN_NAME,
												  key.c_str(),
												  DATA_KEY_SHORT);
					}
					else
					{
						Logger::getLogger()->warn("%s plugin: current element '%s'" \
                                      " doesn't have '%s' property, calculated '0x%X'",
												  PLUGIN_NAME,
												  key.c_str(),
												  DATA_KEY_SHORT,
												  dataTypesShort);
					}
				}
				unsigned short hintChecksum = 0;
				if (cachedValue.HasMember(DATA_KEY_HINT) &&
					cachedValue[DATA_KEY_HINT].IsString())
				{
					string strHint = cachedValue[DATA_KEY_HINT].GetString();
					// The information are stored as string in hexadecimal format
					hintChecksum = stoi (strHint,nullptr,16);
				}
				OMFDataTypes dataType;
				dataType.typeId = typeId;
				dataType.types = dataTypes;
				dataType.typesShort = dataTypesShort;
				dataType.hintChkSum = hintChecksum;
				dataType.namingScheme = NamingScheme;
				dataType.afhHash = AFHHash;
				dataType.afHierarchy = AFHierarchy;
				dataType.afHierarchyOrig = AFHierarchyOrig;

				Logger::getLogger()->debug("%s - AFHHash :%s: AFHierarchy :%s: AFHierarchyOrig :%s: ", __FUNCTION__, AFHHash.c_str(), AFHierarchy.c_str() , AFHierarchyOrig.c_str() );


				Logger::getLogger()->debug("%s - NamingScheme :%ld: ", __FUNCTION__,NamingScheme );

				// Add data into the map
				connInfo->assetsDataTypes[key] = dataType;
			}
		}
	}
	else
	{
		OMFDataTypes dataType;
		dataType.typeId = connInfo->typeId;
		dataType.types = "{}";

		// Add default data into the map
		connInfo->assetsDataTypes[FAKE_ASSET_KEY] = dataType;
	}
}

/**
 * Return the maximum value of type-id, among all entries in the map
 *
 * If the array is empty the connInfo->typeId is returned.
 *
 * @param    connInfo	The CONNECTOR_INFO data scructure
 * @return		The maximum value of type-id found
 */
long getMaxTypeId(CONNECTOR_INFO* connInfo)
{
	long maxId = connInfo->typeId;
	for (auto it = connInfo->assetsDataTypes.begin();
		  it != connInfo->assetsDataTypes.end();
		  ++it)
	{
		if ((*it).second.typeId > maxId)
		{
			maxId = (*it).second.typeId;
		}
	}
	return maxId;
}


/**
 * Calls the PIWebAPI api to retrieve the version
 */
string PIWebAPIGetVersion(CONNECTOR_INFO* connInfo)
{
	string version;
	PIWebAPI *_PIWebAPI;

	_PIWebAPI = new PIWebAPI();

	// Set requested authentication
	_PIWebAPI->setAuthMethod          (connInfo->PIWebAPIAuthMethod);
	_PIWebAPI->setAuthBasicCredentials(connInfo->PIWebAPICredentials);

	version = _PIWebAPI->GetVersion(connInfo->hostAndPort);

	delete _PIWebAPI;

	return version;
}


/**
 * Calls the OCS api to retrieve the authentication token
 */
string OCSRetrieveAuthToken(CONNECTOR_INFO* connInfo)
{
	string token;
	OCS *ocs;

	ocs = new OCS();

	token = ocs->retrieveToken(connInfo->OCSClientId , connInfo->OCSClientSecret);

	delete ocs;

	return token;
}

/**
 * Evaluate if the endpoint is a PI Web API or a Connector Relay.
 *
 * @param    connInfo	The CONNECTOR_INFO data structure
 * @return		        OMF_ENDPOINT values
 */
OMF_ENDPOINT identifyPIServerEndpoint(CONNECTOR_INFO* connInfo)
{
	OMF_ENDPOINT PIServerEndpoint;

	HttpSender *endPoint;
	vector<pair<string, string>> header;
	int httpCode;


	if (connInfo->PIWebAPIAuthMethod.compare("k") == 0)
	{
		endPoint = new LibcurlHttps(connInfo->hostAndPort,
					    connInfo->timeout,
					    connInfo->timeout,
					    connInfo->retrySleepTime,
					    connInfo->maxRetry);
	}
	else
	{
		endPoint = new SimpleHttps(connInfo->hostAndPort,
					   connInfo->timeout,
					   connInfo->timeout,
					   connInfo->retrySleepTime,
					   connInfo->maxRetry);
	}

	// Set requested authentication
	endPoint->setAuthMethod          (connInfo->PIWebAPIAuthMethod);
	endPoint->setAuthBasicCredentials(connInfo->PIWebAPICredentials);

	try
	{
		httpCode = endPoint->sendRequest("GET",
						 connInfo->path,
						 header,
						 "");

		if (httpCode >= 200 && httpCode <= 399)
		{
			PIServerEndpoint = ENDPOINT_PIWEB_API;
			if (connInfo->PIWebAPIAuthMethod == "b")
				Logger::getLogger()->debug("PI Web API end-point basic authorization granted");
		}
		else
		{
			PIServerEndpoint = ENDPOINT_CR;
		}

	}
	catch (exception &ex)
	{
		Logger::getLogger()->warn("PI-Server end-point discovery encountered the error :%s: "
			                  "trying selecting the Connector Relay as an end-point", ex.what());
		PIServerEndpoint = ENDPOINT_CR;
	}

	delete endPoint;

	return (PIServerEndpoint);
}

/**
 * Generate the credentials for the basic authentication
 * encoding user id and password joined by a single colon (:) using base64
 *
 * @param    userId	User id to be used for the generation of the credentials
 * @param    password	Password to be used for the generation of the credentials
 * @return		credentials to be used with the basic authentication
 */
string AuthBasicCredentialsGenerate(string& userId, string& password)
{
	string Credentials;

	Credentials = Crypto::Base64::encode(userId + ":" + password);
	              	
	return (Credentials);
}

/**
 * Configures for Kerberos authentication :
 *   - set the environment KRB5_CLIENT_KTNAME to the position containing the
 *     Kerberos keys, the keytab file.
 *
 * @param   out  keytabEnv       string containing the command to set the
 *                               KRB5_CLIENT_KTNAME environment variable
 * @param        keytabFileName  File name of the keytab file
 *
 */
void AuthKerberosSetup(string& keytabEnv, string& keytabFileName)
{
	string fledgeData = getDataDir ();
	string keytabFullPath = fledgeData + "/etc/kerberos" + "/" + keytabFileName;

	keytabEnv = "KRB5_CLIENT_KTNAME=" + keytabFullPath;
	putenv((char *) keytabEnv.c_str());

	if (access(keytabFullPath.c_str(), F_OK) != 0)
	{
		Logger::getLogger()->error("Kerberos authentication not possible, the keytab file :%s: is missing.", keytabFullPath.c_str());
	}

}
