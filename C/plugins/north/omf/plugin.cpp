/*
 * FogLAMP OMF north plugin.
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

/**
 * Plugin specific default configuration
 */
#define PLUGIN_DEFAULT_CONFIG "\"URL\": { " \
				"\"description\": \"The URL of the PI Connector to send data to\", " \
				"\"type\": \"string\", " \
				"\"default\": \"https://pi-server:5460/ingress/messages\" }, " \
			"\"producerToken\": { " \
				"\"description\": \"The producer token that represents this FogLAMP stream\", " \
				"\"type\": \"string\", \"default\": \"omf_north_0001\" }, " \
			"\"OMFHttpTimeout\": { " \
				"\"description\": \"Timeout in seconds for the HTTP operations with the OMF PI Connector Relay\", " \
				"\"type\": \"integer\", \"default\": \"10\" }, " \
			"\"OMFMaxRetry\": { " \
				"\"description\": \"Max number of retries for the communication with the OMF PI Connector Relay\", " \
				"\"type\": \"integer\", \"default\": \"3\" }, " \
			"\"OMFRetrySleepTime\": { " \
        			"\"description\": \"Seconds between each retry for the communication with the OMF PI Connector Relay, " \
                       		"NOTE : the time is doubled at each attempt.\", \"type\": \"integer\", \"default\": \"1\" }, " \
			"\"StaticData\": { " \
				"\"description\": \"Static data to include in each sensor reading sent to OMF.\", " \
				"\"type\": \"string\", \"default\": \"Location: Palo Alto, Company: Dianomic\" }, " \
			"\"applyFilter\": { " \
        			"\"description\": \"Whether to apply filter before processing the data\", " \
				"\"type\": \"boolean\", \"default\": \"False\" }, " \
			"\"filterRule\": { " \
				"\"description\": \"JQ formatted filter to apply (applicable if applyFilter is True)\", " \
				"\"type\": \"string\", \"default\": \".[]\" }"

#define OMF_PLUGIN_DESC "\"plugin\": {\"description\": \"OMF North C Plugin\", \"type\": \"string\", \"default\": \"omf\"}"

#define PLUGIN_DEFAULT_CONFIG_INFO "{" OMF_PLUGIN_DESC ", " PLUGIN_DEFAULT_CONFIG "}"

/**
 * The OMF plugin interface
 */
extern "C" {

/**
 * The C API plugin information structure
 */
static PLUGIN_INFORMATION info = {
	"OMF",				// Name
	"1.0.0",			// Version
	0,				// Flags
	PLUGIN_TYPE_NORTH,		// Type
	"1.0.0",			// Interface version
	PLUGIN_DEFAULT_CONFIG_INFO   // Configuration
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
	SimpleHttps	*sender;  // HTTPS connection
	OMF 		*omf;     // OMF data protocol
} CONNECTOR_INFO;

static CONNECTOR_INFO connector_info;

static StorageClient* storage;

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
PLUGIN_HANDLE plugin_init(map<string, string>&& configData)
{
	/**
	 * Handle the OMF parameters here
	 */
	ConfigCategory configCategory("cfg", configData["GLOBAL_CONFIGURATION"]);
	string url = configCategory.getValue("URL");
	unsigned int timeout = atoi(configCategory.getValue("OMFHttpTimeout").c_str());
	string producerToken = configCategory.getValue("producerToken");

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

	/**
	 * Allocate the HTTPS handler for "Hostname : port"
	 * connect_timeout and request_timeout.
	 * Default is no timeout at all
	 */

	string hostAndPort(hostName + ":" + port);	
	connector_info.sender = new SimpleHttps(hostAndPort, timeout, timeout);

	// Allocate the OMF data protocol
	connector_info.omf = new OMF(*connector_info.sender,
				     path,
				     typesId,
				     producerToken);

	Logger::getLogger()->info("OMF plugin configured: URL=%s, "
				  "producerToken=%s, OMF_types_id=%s",
				  url.c_str(),
				  producerToken.c_str(),
				  typesId.c_str());


	// TODO: return a more useful data structure for pluin handle
	string* handle = new string("Init done");

	return (PLUGIN_HANDLE)handle;
}

/**
 * Send Readings data to historian server
 */
uint32_t plugin_send(const PLUGIN_HANDLE handle,
		     const vector<Reading *> readings)
{
	return connector_info.omf->sendToServer(readings);
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
	// Delete connector data
	delete connector_info.sender;
	delete connector_info.omf;

	// Delete the handle
	string* data = (string *)handle;
        delete data;
}

// End of extern "C"
};
