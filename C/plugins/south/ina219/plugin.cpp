/*
 * FogLAMP south plugin.
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <ina219.h>
#include <plugin_api.h>
#include <stdio.h>
#include <stdlib.h>
#include <strings.h>
#include <string>
#include <logger.h>
#include <plugin_exception.h>
#include <config_category.h>
#include <rapidjson/document.h>

using namespace std;

/**
 * Default configuration
 */
#define CONFIG	"{\"plugin\" : { \"description\" : \"INA219 current and voltage sensor\", " \
			"\"type\" : \"string\", \"default\" : \"ina219\" }, " \
		"\"asset\" : { \"description\" : \"Asset name\", "\
			"\"type\" : \"string\", \"default\" : \"electrical\" }, " \
		"\"address\" : { \"description\" : \"Address of IAN219\", " \
			"\"type\" : \"integer\", \"default\" : \"64\" }, "\
		"\"range\" : { \"description\" : \"Required range setting\", " \
			"\"type\" : \"string\", \"default\" : \"32V2A\" } "\
			"}"

/**
 * The INA219 plugin interface
 */
extern "C" {

/**
 * The plugin information structure
 */
static PLUGIN_INFORMATION info = {
	"ina219",                 // Name
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
INA219 *ina219 = 0;
string	address, range;

	if (config->itemExists("address"))
	{
		address = config->getValue("address");
		ina219 = new INA219(atoi(address.c_str()));
	}
	if (config->itemExists("range"))
	{
		INA219_CONFIGURATION conf = CONF_32V_2A;
		range = config->getValue("range");
		if (range.compare("32V2A") == 0)
		{
			conf = CONF_32V_2A;
		}
		else if (range.compare("32V1A") == 0)
		{
			conf = CONF_32V_1A;
		}
		else if (range.compare("16V400mA") == 0)
		{
			conf = CONF_16V_400MA;
		}
		ina219->configure(conf);
	}
	else
	{
		ina219->configure(CONF_32V_2A);
	}

	if (config->itemExists("asset"))
	{
		ina219->setAssetName(config->getValue("asset"));
	}
	else
	{
		ina219->setAssetName("electrical");
	}

	return (PLUGIN_HANDLE)ina219;
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
INA219 *ina219 = (INA219 *)handle;

	if (!handle)
		throw new exception();
	return ina219->takeReading();
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
INA219 *ina219 = (INA219 *)handle;

	delete ina219;
}
};
