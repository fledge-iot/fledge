/*
 * FogLAMP PI Server north plugin.
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Massimiliano Pinto
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
#include <storage_client.h>

using namespace std;

#define PLUGIN_NAME "PI_Server_V2"

/**
 * Plugin specific default configuration
 */
#define PLUGIN_DEFAULT_CONFIG \
			"\"URL\": { " \
				"\"description\": \"The URL of the PI Connector to send data to\", " \
				"\"type\": \"string\", " \
				"\"default\": \"https://pi-server:5460/ingress/messages\", " \
				"\"order\": \"1\" }, " \
			"\"producerToken\": { " \
				"\"description\": \"The producer token that represents this FogLAMP stream\", " \
				"\"type\": \"string\", \"default\": \"omf_north_0001\", " \
				"\"order\": \"2\" }, " \
			"\"StaticData\": { " \
				"\"description\": \"Static data to include in each sensor reading sent to the PI Server.\", " \
				"\"type\": \"string\", \"default\": \"Location: Palo Alto, Company: Dianomic\", " \
				"\"order\": \"4\" }, " \
			"\"OMFRetrySleepTime\": { " \
        			"\"description\": \"Seconds between each retry for the communication with the OMF PI Connector Relay, " \
                       		"NOTE : the time is doubled at each attempt.\", \"type\": \"integer\", \"default\": \"1\", " \
				"\"order\": \"9\" }, " \
			"\"OMFMaxRetry\": { " \
				"\"description\": \"Max number of retries for the communication with the OMF PI Connector Relay\", " \
				"\"type\": \"integer\", \"default\": \"3\", " \
				"\"order\": \"10\" }, " \
			"\"OMFHttpTimeout\": { " \
				"\"description\": \"Timeout in seconds for the HTTP operations with the OMF PI Connector Relay\", " \
				"\"type\": \"integer\", \"default\": \"10\", " \
				"\"order\": \"13\" }, " \
			"\"formatInteger\": { " \
        			"\"description\": \"OMF format property to apply to the type Integer\", " \
				"\"type\": \"string\", \"default\": \"int64\", " \
				"\"order\": \"14\" }, " \
			"\"formatNumber\": { " \
        			"\"description\": \"OMF format property to apply to the type Number\", " \
				"\"type\": \"string\", \"default\": \"float64\", " \
				"\"order\": \"15\" }, " \
			"\"compression\": { " \
        			"\"description\": \"Compress readings data before sending to PI server\", " \
				"\"type\": \"boolean\", \"default\": \"False\", " \
				"\"order\": \"16\" } "

#define OMF_PLUGIN_DESC "\"plugin\": {\"description\": \"PI Server North C Plugin\", \"type\": \"string\", \"default\": \"" PLUGIN_NAME "\", \"readonly\": \"true\"}"

#define PLUGIN_DEFAULT_CONFIG_INFO "{" OMF_PLUGIN_DESC ", " PLUGIN_DEFAULT_CONFIG "}"

/**
 * The PI Server plugin interface
 */
extern "C" {

/**
 * The C API plugin information structure
 */
static PLUGIN_INFORMATION info = {
	PLUGIN_NAME,		        // Name
	"1.0.0",			// Version
	0,				// Flags
	PLUGIN_TYPE_NORTH,		// Type
	"1.0.0",			// Interface version
	PLUGIN_DEFAULT_CONFIG_INFO      // Configuration
};

static const string omf_types_default_config =
			"\"type-id\": { "
				"\"description\": \"Identify sensor and measurement types\", "
				"\"type\": \"integer\", \"default\": \"0002\" }";

static const map<const string, const string> plugin_configuration = {
					{
						"OMF_TYPES",
						omf_types_default_config
					},
					{
						"PLUGIN",
						string(PLUGIN_DEFAULT_CONFIG)
					},
				 };

/**
 * Historian PI Server connector info
 */
typedef struct
{
	SimpleHttps	*sender;	// HTTPS connection
	OMF 		*omf;		// OMF data protocol
	bool		compression;	// whether to compress readings' data
	string		hostAndPort;	// hostname:port for SimpleHttps
	unsigned int	timeout;	// connect and operation timeout
	string		path;		// PI Server application path
	string		typesId;	// OMF protocol type-id prefix
	string		producerToken;	// PI Server connector token
	string		formatNumber;	// OMF protocol Number format
	string		formatInteger;	// OMF protocol Integer format
} CONNECTOR_INFO;


/**
 * Return the information about this plugin
 */
PLUGIN_INFORMATION *plugin_info()
{
	return &info;
}

/**
 * Return default plugin configuration:
 * plugin specific and types_id
 */
const map<const string, const string>& plugin_config()
{
	return plugin_configuration;
}

/**
 * Initialise the plugin with configuration.
 *
 * This funcion is called to get the plugin handle.
 */
PLUGIN_HANDLE plugin_init(map<string, string>& configData)
{
	/**
	 * Handle the PI Server parameters here
	 */
	ConfigCategory configCategory("cfg", configData["GLOBAL_CONFIGURATION"]);
	string url = configCategory.getValue("URL");
	unsigned int timeout = atoi(configCategory.getValue("OMFHttpTimeout").c_str());
	string producerToken = configCategory.getValue("producerToken");

	string formatNumber = configCategory.getValue("formatNumber");
	string formatInteger = configCategory.getValue("formatInteger");

	/**
	 * Handle the OMF_TYPES parameters here
	 */
	ConfigCategory configTypes("types", configData["OMF_TYPES"]);
	string typesId = configTypes.getValue("type-id");

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
	// Set configuration felds
	connInfo->hostAndPort = hostAndPort;
	connInfo->path = path;
	connInfo->timeout = timeout;
	connInfo->typesId = typesId;
	connInfo->producerToken = producerToken;
	connInfo->formatNumber = formatNumber;
	connInfo->formatInteger = formatInteger;

	// Use compression ?
	string compr = configCategory.getValue("compression");
	if (compr == "True" || compr == "true" || compr == "TRUE")
		connInfo->compression = true;
	else
		connInfo->compression = false;


	// Log plugin configuration
	Logger::getLogger()->info("%s plugin configured: URL=%s, "
				  "producerToken=%s, OMF_types_id=%s, compression=%s",
				  PLUGIN_NAME,
				  url.c_str(),
				  producerToken.c_str(),
				  typesId.c_str(),
				  connInfo->compression ? "True" : "False");

	return (PLUGIN_HANDLE)connInfo;
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
	connInfo->sender = new SimpleHttps(connInfo->hostAndPort,
					   connInfo->timeout,
					   connInfo->timeout);
  
	// Allocate the PI Server data protocol
	connInfo->omf = new OMF(*connInfo->sender,
				connInfo->path,
				connInfo->typesId,
				connInfo->producerToken);

	// Set OMF FormatTypes  
	connInfo->omf->setFormatType(OMF_TYPE_FLOAT,
				     connInfo->formatNumber);
	connInfo->omf->setFormatType(OMF_TYPE_INTEGER,
				     connInfo->formatInteger);

	// Send data
	uint32_t ret = connInfo->omf->sendToServer(readings,
						   connInfo->compression);

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
 */
void plugin_shutdown(PLUGIN_HANDLE handle)
{
	// Delete the handle
	CONNECTOR_INFO* connInfo = (CONNECTOR_INFO *) handle;
	delete connInfo;
}

// End of extern "C"
};
