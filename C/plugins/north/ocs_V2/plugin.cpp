/*
 * FogLAMP OCS north plugin.
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Stefano Simonelli
 */
#include <plugin_api.h>
#include <stdio.h>
#include <stdlib.h>
#include <strings.h>
#include <string>
#include <logger.h>
#include <plugin_exception.h>
#include <iostream>
#include <omf.h>
#include <simple_https.h>
#include <config_category.h>
#include "rapidjson/writer.h"
#include "rapidjson/stringbuffer.h"
#include "json_utils.h"

using namespace std;
using namespace rapidjson;

#define PLUGIN_NAME "ocs_V2"
#define TYPE_ID_KEY "type-id"
#define TYPE_ID_DEFAULT "1"

/**
 * Plugin specific default configuration
 */
#define PLUGIN_DEFAULT_CONFIG \
			"\"URL\": { " \
				"\"description\": \"The URL of OCS (OSIsoft Cloud Services), " \
				"NOTE : TENANT_ID_PLACEHOLDER and NAMESPACE_ID_PLACEHOLDER, if present, will be replaced with the values of tenant_id and namespace\", " \
				"\"type\": \"string\", " \
				"\"default\": \"https://dat-a.osisoft.com:443/api/tenants/TENANT_ID_PLACEHOLDER/namespaces/NAMESPACE_ID_PLACEHOLDER/omf\", " \
				"\"order\": \"1\", \"displayName\" : \"URL\" }, " \
			"\"producerToken\": { " \
				"\"description\": \"The producer token used to authenticate as a valid publisher and required to ingest data into OCS using OMF.\", " \
				"\"type\": \"string\", \"default\": \"omf_north_0001\", " \
				"\"order\": \"2\", \"displayName\" : \"Producer Token\" }, " \
			"\"source\": {" \
				"\"description\": \"Defines the source of the data to be sent on the stream, " \
				"this may be one of either readings, statistics or audit.\", \"type\": \"enumeration\", " \
				"\"default\": \"readings\", "\
				"\"options\": [\"readings\", \"statistics\"], " \
				"\"order\": \"3\", \"displayName\" : \"Data Source\"  }, " \
			"\"StaticData\": { " \
				"\"description\": \"Static data to include in each sensor reading sent to OCS.\", " \
				"\"type\": \"string\", \"default\": \"Location: Palo Alto, Company: Dianomic\", " \
				"\"order\": \"4\", \"displayName\" : \"Static Data\" }, " \
			"\"OMFRetrySleepTime\": { " \
        			"\"description\": \"Seconds between each retry for the communication with OCS, " \
                       		"NOTE : the time is doubled at each attempt.\", \"type\": \"integer\", \"default\": \"1\", " \
				"\"order\": \"9\", \"displayName\" : \"Sleep Time Retry\" }, " \
			"\"OMFMaxRetry\": { " \
				"\"description\": \"Max number of retries for the communication with OCS\", " \
				"\"type\": \"integer\", \"default\": \"3\", " \
				"\"order\": \"10\", \"displayName\" : \"Maximum Retry\" }, " \
			"\"OMFHttpTimeout\": { " \
				"\"description\": \"Timeout in seconds for the HTTP operations with OCS\", " \
				"\"type\": \"integer\", \"default\": \"10\", " \
				"\"order\": \"13\", \"displayName\" : \"HTTP Timeout\" }, " \
			"\"formatInteger\": { " \
        			"\"description\": \"OMF format property to apply to the type Integer\", " \
				"\"type\": \"string\", \"default\": \"int64\", " \
				"\"order\": \"14\", \"displayName\" : \"Integer Format\" }, " \
			"\"formatNumber\": { " \
        			"\"description\": \"OMF format property to apply to the type Number\", " \
				"\"type\": \"string\", \"default\": \"float64\", " \
				"\"order\": \"15\", \"displayName\" : \"Number Format\" }, " \
			"\"compression\": { " \
        			"\"description\": \"Compress readings data before sending to OCS\", " \
				"\"type\": \"boolean\", \"default\": \"True\", " \
				"\"order\": \"16\", \"displayName\" : \"Compression\" }, " \
			"\"streamId\": {" \
				"\"description\": \"Identifies the specific stream to handle and the related information," \
				" among them the ID of the last object streamed.\", " \
				"\"type\": \"integer\", \"default\": \"0\", " \
				"\"readonly\": \"true\" }," \
			"\"namespace\" : {"\
				"\"description\" : \"Specifies the OCS namespace where the information are stored and it is used for the interaction with the OCS API\", "\
				"\"type\" : \"string\", "\
				"\"default\": \"10\", " \
				"\"order\": \"17\", \"displayName\" : \"Namespace\"  " \
			"}, "\
			"\"tenant_id\" : {"\
				"\"description\" : \"Tenant id associated to the specific OCS account\", "\
				"\"type\" : \"string\", "\
				"\"default\": \"ocs_tenant_id\", " \
				"\"order\": \"18\", \"displayName\" : \"Tenant ID\"  " \
			"}, "\
			"\"client_id\" : {"\
				"\"description\" : \"Client id associated to the specific OCS account, it is used to authenticate the source for using the OCS API\", "\
				"\"type\" : \"string\", "\
				"\"default\": \"ocs_client_id\", " \
				"\"order\": \"19\", \"displayName\" : \"Client ID\"  " \
			"}, "\
			"\"client_secret\" : {"\
				"\"description\" : \"Client secret associated to the specific OCS account, it is used to authenticate the source for using the OCS API\", "\
				"\"type\" : \"string\", "\
				"\"default\": \"ocs_client_secret\", " \
				"\"order\": \"20\", \"displayName\" : \"Client Secret\"  " \
			"}, "\
			"\"notBlockingErrors\": {" \
				"\"description\": "\
					"\"These errors are considered not blocking in the communication with the PI Server, " \
					  " the sending operation will proceed with the next block of data if one of these is encountered\" ," \
				"\"type\": \"JSON\", " \
				"\"default\": \"{\\\"errors400\\\": "\
		                        "["\
		                        "]"\
                                "}\", " \
				"\"order\": \"21\" ,"  \
				"\"readonly\": \"true\" " \
			"} "
			// The notBlockingErrors list is empty as OCS is curretly not raising errors, PI-SERVER does.



#define OMF_PLUGIN_DESC "\"plugin\": {\"description\": \"OCS (OSIsoft Cloud Services) North C Plugin\", \"type\": \"string\", \"default\": \"" PLUGIN_NAME "\", \"readonly\": \"true\"}"

#define PLUGIN_DEFAULT_CONFIG_INFO "{" OMF_PLUGIN_DESC ", " PLUGIN_DEFAULT_CONFIG "}"

/**
 * The OCS plugin interface
 */
extern "C" {

/**
 * The C API plugin information structure
 */
static PLUGIN_INFORMATION info = {
	PLUGIN_NAME,		        // Name
	"1.0.0",			// Version
	SP_PERSIST_DATA,		// Flags
	PLUGIN_TYPE_NORTH,		// Type
	"1.0.0",			// Interface version
	PLUGIN_DEFAULT_CONFIG_INFO      // Configuration
};

/**
 * Historian OCS Server connector info
 */
typedef struct
{
	SimpleHttps	*sender;	// HTTPS connection
	OMF 		*omf;		// OMF data protocol
	bool		compression;	// whether to compress readings' data
	string		hostAndPort;	// hostname:port for SimpleHttps
	unsigned int	retrySleepTime;	// Seconds between each retry
	unsigned int	maxRetry;	// Max number of retries in the communication
	unsigned int	timeout;	// connect and operation timeout
	string		path;		// OCS application path
	string		typeId;		// OMF protocol type-id prefix
	string		producerToken;	// OCS connector token
	string		formatNumber;	// OMF protocol Number format
	string		formatInteger;	// OMF protocol Integer format
	// Errors considered not blocking in the communication with the PI Server
	std::vector<std::string>
			notBlockingErrors;

} CONNECTOR_INFO;


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
	/**
	 * Handle the OCS parameters here
	 */
	string url = configData->getValue("URL");

	unsigned int retrySleepTime = atoi(configData->getValue("OMFRetrySleepTime").c_str());
	unsigned int maxRetry = atoi(configData->getValue("OMFMaxRetry").c_str());
	unsigned int timeout = atoi(configData->getValue("OMFHttpTimeout").c_str());

	string producerToken = configData->getValue("producerToken");

	string formatNumber = configData->getValue("formatNumber");
	string formatInteger = configData->getValue("formatInteger");

	string tenant_id = configData->getValue("tenant_id");
	string namespace_id = configData->getValue("namespace");

	// TENANT_ID_PLACEHOLDER and NAMESPACE_ID_PLACEHOLDER, if present, will be replaced with the values of tenant_id and namespace_id
	string pattern  = "TENANT_ID_PLACEHOLDER";

	if (url.find(pattern) != string::npos)
		url.replace(url.find(pattern), pattern.length(), tenant_id);

	pattern  = "NAMESPACE_ID_PLACEHOLDER";

	if (url.find(pattern) != string::npos)
		url.replace(url.find(pattern), pattern.length(), namespace_id);

	/**
	 * Extract host, port, path from URL
	 */
	size_t findProtocol = url.find_first_of(":");
	string protocol = url.substr(0,findProtocol);

	string tmpUrl = url.substr(findProtocol + 3);
	size_t findPort = tmpUrl.find_first_of(":");
	string hostName = tmpUrl.substr(0, findPort);

	size_t findPath = tmpUrl.find_first_of("/");
	string port = tmpUrl.substr(findPort + 1 , findPath - findPort -1);
	string path = tmpUrl.substr(findPath);

	string hostAndPort(hostName + ":" + port);	

	// Allocate connector struct
	CONNECTOR_INFO* connInfo = new CONNECTOR_INFO;
	// Set configuration fields
	connInfo->hostAndPort = hostAndPort;
	connInfo->path = path;
	connInfo->retrySleepTime = retrySleepTime;
	connInfo->maxRetry = maxRetry;
	connInfo->timeout = timeout;
	connInfo->typeId = TYPE_ID_DEFAULT;
	connInfo->producerToken = producerToken;
	connInfo->formatNumber = formatNumber;
	connInfo->formatInteger = formatInteger;

	// Use compression ?
	string compr = configData->getValue("compression");
	if (compr == "True" || compr == "true" || compr == "TRUE")
		connInfo->compression = true;
	else
		connInfo->compression = false;

	// Set the list of errors considered not blocking in the communication
	// with the PI Server
	JSONStringToVectorString(connInfo->notBlockingErrors ,
	                         configData->getValue("notBlockingErrors"),
	                         std::string("errors400"));

	// Log plugin configuration
	Logger::getLogger()->info("%s plugin configured: URL=%s, "
				  "producerToken=%s, compression=%s",
				  PLUGIN_NAME,
				  url.c_str(),
				  producerToken.c_str(),
				  connInfo->compression ? "True" : "False");

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
		JSONData[TYPE_ID_KEY].IsString())
	{
		// Update type-id in PLUGIN_HANDLE object
		connInfo->typeId = JSONData[TYPE_ID_KEY].GetString();
	}
	else
	{
		logger->error("%s plugin error: key " TYPE_ID_KEY " not found "
			      " or not valid in plugin data JSON object'%s'",
			      PLUGIN_NAME,
			      storedData.c_str());
	}
	// Log plugin configuration
	Logger::getLogger()->info("%s plugin is using OMF %s=%s",
				  PLUGIN_NAME,
				  TYPE_ID_KEY,
				  connInfo->typeId.c_str());
}

/**
 * Send Readings data to OCS
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
	connInfo->sender = new SimpleHttps(connInfo->hostAndPort,
					   connInfo->timeout,
					   connInfo->timeout,
					   connInfo->retrySleepTime,
					   connInfo->maxRetry);
  
	// Allocate the OCS data protocol
	connInfo->omf = new OMF(*connInfo->sender,
				connInfo->path,
				connInfo->typeId,
				connInfo->producerToken);

	// Set OMF FormatTypes  
	connInfo->omf->setFormatType(OMF_TYPE_FLOAT,
				     connInfo->formatNumber);
	connInfo->omf->setFormatType(OMF_TYPE_INTEGER,
				     connInfo->formatInteger);

	connInfo->omf->setNotBlockingErrors(connInfo->notBlockingErrors);

	// Send data
	uint32_t ret = connInfo->omf->sendToServer(readings,
						   connInfo->compression);

	// Detect typeId change in OMF class
	if (connInfo->omf->getTypeId().compare(connInfo->typeId) != 0)
	{
		// Update typeId in plugin handle
		connInfo->typeId = connInfo->omf->getTypeId();
		// Log change
		Logger::getLogger()->info("%s plugin: a new OMF %s (%s) has been created.",
					  PLUGIN_NAME,
					  TYPE_ID_KEY,
					  connInfo->typeId.c_str());
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
 * @param handle    The plugin handle
 * @return	    A string with JSON plugin data
 *		    the caller will persist
 */
string plugin_shutdown(PLUGIN_HANDLE handle)
{
	// Delete the handle
	CONNECTOR_INFO* connInfo = (CONNECTOR_INFO *) handle;

	// Create save data
	string saveData("{\"" TYPE_ID_KEY "\": \"" + connInfo->typeId + "\"}");

        // Log saving the plugin configuration
        Logger::getLogger()->info("%s plugin: saving plugin_data '%s'",
                                  PLUGIN_NAME,
                                  saveData.c_str());

	// Delete plugin handle
	delete connInfo;

	// Return current plugin data to save
	return saveData;
}

// End of extern "C"
};
