/*
 * FogLAMP south plugin.
 *
 * Copyright (c) 2018 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <modbus_south.h>
#include <plugin_api.h>
#include <stdio.h>
#include <stdlib.h>
#include <strings.h>
#include <string>
#include <logger.h>
#include <plugin_exception.h>
#include <config_category.h>

using namespace std;

/**
 * Default configuration
 */
#define CONFIG	"{\"plugin\" : { \"description\" : \"Modbus TCP and RTU plugin\", " \
		"\"type\" : \"string\", \"default\" : \"foglamp-modbus\" }, " \
		"\"address\" : { \"description\" : \"Address of Modbus TCP server\", " \
		"\"type\" : \"string\", \"default\" : \"\" }, "\
		"\"port\" : { \"description\" : \"Port of Modbus TCP server\", " \
		"\"type\" : \"int\", \"default\" : \"502\" }, "\
		"\"device\" : { \"description\" : \"Device for Modbus RTU\", " \
		"\"type\" : \"int\", \"default\" : \"\" }, "\
		"\"baud\" : { \"description\" : \"Baud rate  of Modbus RTU\", " \
		"\"type\" : \"int\", \"default\" : \"9600\" }, "\
		"\"bits\" : { \"description\" : \"Number of data bits for Modbus RTU\", " \
		"\"type\" : \"int\", \"default\" : \"7\" }, "\
		"\"stopbits\" : { \"description\" : \"Number of stop bits for Modbus RTU\", " \
		"\"type\" : \"int\", \"default\" : \"2\" }, "\
" }"

/**
 * The Modbus plugin interface
 */
extern "C" {

/**
 * The plugin information structure
 */
static PLUGIN_INFORMATION info = {
	"modbus",                 // Name
	"1.0.0",                  // Version
	0,    			  // Flags
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
	Modbus *modbus = new Modbus("127.0.0.1", 502);

	return (PLUGIN_HANDLE)modbus;
}

/**
 * Start the Async handling for the plugin
 */
void plugin_start(PLUGIN_HANDLE *handle)
{
}

/**
 * Poll for a plugin reading
 */
Reading plugin_poll(PLUGIN_HANDLE *handle)
{
Modbus *modbus = (Modbus *)handle;

	return modbus->takeReading();
}

/**
 * Reconfigure the plugin
 */
void plugin_reconfigure(PLUGIN_HANDLE *handle, string& newConfig)
{
}

/**
 * Shutdown the plugin
 */
void plugin_shutdown(PLUGIN_HANDLE *handle)
{
Modbus *modbus = (Modbus *)handle;

	delete modbus;
}
};
