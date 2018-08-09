/*
 * FogLAMP south plugin.
 *
 * Copyright (c) 2018 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Amandeep Singh Arora
 */
#include <dht11.h>
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
#define CONFIG  "{\"plugin\" : { \"description\" : \"DHT11 C south plugin\", " \
                        "\"type\" : \"string\", \"default\" : \"foglamp-dht11\" }, " \
                "\"asset\" : { \"description\" : \"Asset name\", "\
                        "\"type\" : \"string\", \"default\" : \"dht11\" }, " \
                "\"pin\" : { \"description\" : \"RPi pin to which DHT11 is attached\", " \
                        "\"type\" : \"integer\", \"default\" : \"7\" } "\
                "}"


/**
 * The DHT11 plugin interface
 */
extern "C" {

/**
 * The plugin information structure
 */
static PLUGIN_INFORMATION info = {
	"DHT11",                  // Name
	"1.0.0",                  // Version
	0,    			  // Flags
	PLUGIN_TYPE_SOUTH,        // Type
	"1.0.0",                  // Interface version
	CONFIG                    // Default configuration
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
	unsigned int pin;

	if (config->itemExists("pin"))
        {
                pin = stoul(config->getValue("pin"), nullptr, 0);
        }

	DHT11 *dht11= new DHT11(pin);

	if (config->itemExists("asset"))
                dht11->setAssetName(config->getValue("asset"));
        else
                dht11->setAssetName("dht11");

	Logger::getLogger()->info("m_assetName set to %s", dht11->getAssetName());

	return (PLUGIN_HANDLE)dht11;
}

/**
 * Poll for a plugin reading
 */
Reading plugin_poll(PLUGIN_HANDLE *handle)
{
	DHT11 *dht11 = (DHT11*)handle;
	return dht11->takeReading();
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
	DHT11 *dht11 = (DHT11*)handle;
	delete dht11;
}
};

