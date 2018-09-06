/*
 * FogLAMP south plugin.
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <opcua.h>
#include <plugin_api.h>
#include <stdio.h>
#include <stdlib.h>
#include <strings.h>
#include <string>
#include <logger.h>
#include <plugin_exception.h>
#include <config_category.h>
#include <rapidjson/document.h>

typedef void (*INGEST_CB)(void *, Reading);

using namespace std;

/**
 * Default configuration
 */
#define CONFIG	"{\"plugin\" : { \"description\" : \"Simple OPC UA data change plugin\", " \
			"\"type\" : \"string\", \"default\" : \"opcua\" }, " \
		"\"asset\" : { \"description\" : \"Asset name\", "\
			"\"type\" : \"string\", \"default\" : \"opcua\" }, " \
		"\"url\" : { \"description\" : \"URL of the OPC UA Server\", "\
			"\"type\" : \"string\", \"default\" : \"opc.tcp://mark.local:53530/OPCUA/SimulationServer\" }, " \
		"\"subscription\" : { \"description\" : \"Variable to observe changes in\", " \
			"\"type\" : \"JSON\", \"default\" : \"{ \\\"subscriptions\\\" : [  \\\"5:Simulation\\\" ] }\" } " \
			"}"

/**
 * The OPCUA plugin interface
 */
extern "C" {

/**
 * The plugin information structure
 */
static PLUGIN_INFORMATION info = {
	"upcua",                  // Name
	"1.0.0",                  // Version
	SP_ASYNC, 		  // Flags
	PLUGIN_TYPE_SOUTH,        // Type
	"1.0.0",                  // Interface version
	CONFIG			  // Default configuration
};

/**
 * Return the information about this plugin
 */
PLUGIN_INFORMATION *plugin_info()
{
	return &info;
}

/**
 * Initialise the plugin, called to get the plugin handle
 */
PLUGIN_HANDLE plugin_init(ConfigCategory *config)
{
OPCUA	*opcua;
string	url;


	if (config->itemExists("url"))
	{
		url = config->getValue("url");
		opcua = new OPCUA(url);
	}
	else
	{
		Logger::getLogger()->fatal("UPC UA plugin is missing a URL");
		throw exception();
	}


	if (config->itemExists("asset"))
	{
		opcua->setAssetName(config->getValue("asset"));
	}
	else
	{
		opcua->setAssetName("opcua");
	}

	// Now add the subscription data
	string map = config->getValue("subscription");
	rapidjson::Document doc;
	doc.Parse(map.c_str());
	if (!doc.HasParseError())
	{
		if (doc.HasMember("subscriptions") && doc["subscriptions"].IsArray())
		{
			const rapidjson::Value& subs = doc["subscriptions"];
			for (rapidjson::SizeType i = 0; i < subs.Size(); i++)
                        {
                                opcua->addSubscription(subs[i].GetString());
                        }
		}
		else
		{
			Logger::getLogger()->fatal("UPC UA plugin is missing a subscriptions array");
			throw exception();
		}
	}

	return (PLUGIN_HANDLE)opcua;
}

/**
 * Start the Async handling for the plugin
 */
void plugin_start(PLUGIN_HANDLE *handle)
{
OPCUA *opcua = (OPCUA *)handle;


	if (!handle)
		return;
	opcua->start();
}

/**
 * Register ingest callback
 */
void plugin_register_ingest(PLUGIN_HANDLE *handle, INGEST_CB cb, void *data)
{
OPCUA *opcua = (OPCUA *)handle;

	if (!handle)
		throw new exception();
	opcua->registerIngest(data, cb);
}

/**
 * Poll for a plugin reading
 */
Reading plugin_poll(PLUGIN_HANDLE *handle)
{
OPCUA *opcua = (OPCUA *)handle;

	throw runtime_error("OPCUA is an async plugin, poll should not be called");
}

/**
 * Reconfigure the plugin
 *
 * TODO Dynamic reconfiguration
 */
void plugin_reconfigure(PLUGIN_HANDLE *handle, string& newConfig)
{
}

/**
 * Shutdown the plugin
 */
void plugin_shutdown(PLUGIN_HANDLE *handle)
{
OPCUA *opcua = (OPCUA *)handle;

	opcua->stop();
	delete opcua;
}
};
