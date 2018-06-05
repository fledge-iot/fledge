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
		"\"map\" : { \"description\" : \"Modbus register map\", " \
		"\"type\" : \"json\", \"default\" : { " \
			"[ { \"asset\" : \"temperature\", \"register\" : \"7\" }," \
			"{ \"asset\" : \"humidity\", \"register\" : \"8\" } ]" \
			"} " \
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
Modbus *modbus = 0;
string	device, address;

	if (config->itemExists("address"))
	{
		address = config->getValue("address");
		if (address.compare("") == 0)		// Not empty
		{
			unsigned short port = 502;
			if (config->itemExists("port"))
			{
				string value = config->getValue("port");
				port = (unsigned short)atoi(value.c_str());
			}
			modbus = new Modbus(address.c_str(), port);
		}
	}
	if (config->itemExists("device"))
	{
		device = config->getValue("device");
		if (device.compare("") == 0)
		{
			int baud = 9600;
			char parity = 'E';
			int bits = 7;
			int stopBits = 2;
			if (config->itemExists("baud"))
			{
				string value = config->getValue("baud");
				baud = atoi(value.c_str());
			}
			if (config->itemExists("parity"))
			{
				string value = config->getValue("parity");
				if (value.compare("even") == 0)
				{
					parity = 'E';
				}
				else if (value.compare("odd") == 0)
				{
					parity = 'O';
				}
				else if (value.compare("none") == 0)
				{
					parity = 'N';
				}
			}
			if (config->itemExists("bits"))
			{
				string value = config->getValue("bits");
				bits = atoi(value.c_str());
			}
			if (config->itemExists("stopBits"))
			{
				string value = config->getValue("stopBits");
				stopBits = atoi(value.c_str());
			}
			modbus = new Modbus(device.c_str(), baud, parity, bits, stopBits);
		}
	}

	modbus->setAssetName(config->getValue("asset"));

	return (PLUGIN_HANDLE)modbus;
}

/**
 * Start the Async handling for the plugin
 */
void plugin_start(PLUGIN_HANDLE *handle)
{
	if (!handle)
		return;
}

/**
 * Poll for a plugin reading
 */
Reading plugin_poll(PLUGIN_HANDLE *handle)
{
Modbus *modbus = (Modbus *)handle;

	if (!handle)
		throw new exception();
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
