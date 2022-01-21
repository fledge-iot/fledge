/*
 * Fledge south plugin.
 *
 * Copyright (c) 2022 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <plugin_api.h>
#include <stdio.h>
#include <stdlib.h>
#include <strings.h>
#include <string>
#include <logger.h>
#include <plugin_exception.h>
#include <config_category.h>
#include <version.h>
#include <reading.h>
#include <dpimage.h>

typedef void (*INGEST_CB)(void *, Reading);

#define PLUGIN_NAME "testcard"

using namespace std;

/**
 * The default configuration for the Flir plugin.
 */
static const char *default_config = QUOTE({
	"plugin" : { 
		"description" :  "Plugin for image testcard production",
		"type" : "string",
		"default" : PLUGIN_NAME, 
		"readonly" : "true"
		}, 
	"asset" : { 
		"description" : "Asset name to use",
		"type" : "string",
		"default" : "testcard",
		"displayName": "Asset Name",
		"mandatory": "true",
		"order" : "1"
	       	},
	"depth" : {
		"description" : "Depth of the testcard to create",
		"type" : "enumeration",
		"options" : [ "8", "16", "24" ],
		"default" : "8",
		"displayName": "Depth",
		"mandatory": "true",
		"order" : "2"
		}
	});
		  
/**
 * The Flir plugin interface
 */
extern "C" {

/**
 * The plugin information structure
 */
static PLUGIN_INFORMATION info = {
	PLUGIN_NAME,              // Name
	VERSION,                  // Version
	SP_CONTROL,  	  	  // Flags
	PLUGIN_TYPE_SOUTH,        // Type
	"1.0.0",                  // Interface version
	default_config            // Default configuration
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
ConfigCategory *newconfig;

	newconfig = new ConfigCategory(*config);
	return (PLUGIN_HANDLE)newconfig;
}

/**
 * Start the Async handling for the plugin
 */
void plugin_start(PLUGIN_HANDLE *handle)
{
ConfigCategory *conf = (ConfigCategory *)handle;

	if (!handle)
		return;
}


/**
 * Poll for a plugin reading
 */
Reading plugin_poll(PLUGIN_HANDLE *handle)
{
ConfigCategory *conf = (ConfigCategory *)handle;

	string d = conf->getValue("depth");
	int depth = strtol(d.c_str(), NULL, 10);
	switch (depth)
	{
		case 8:
			{
			void *data = malloc(256 * 256);
			uint8_t *ptr = (uint8_t *)data;
			for (int i = 0; i < 256; i++)
			{
				for (int j = 0; j < 256; j++)
				{
					*ptr++ = i;
				}
			}
			DPImage *image = new DPImage(256, 256, 8, data);
			DatapointValue img(image);
			return Reading(conf->getValue("asset"), new Datapoint("testcard", img));
			}
		case 16:
			{
			void *data = malloc(256 * 256 * 2);
			uint16_t *ptr = (uint16_t *)data;
			for (int i = 0; i < 256; i++)
			{
				for (int j = 0; j < 256; j++)
				{
					*ptr++ = i * i;
				}
			}
			DPImage *image = new DPImage(256, 256, 16, data);
			DatapointValue img(image);
			return Reading(conf->getValue("asset"), new Datapoint("testcard", img));
			}
		case 24:
			{
			void *data = malloc(256 * 256 * 3);
			uint8_t *ptr = (uint8_t *)data;
			for (int i = 0; i < 32; i++)
			{
				for (int j = 0; j < 256; j++)
				{
					*ptr++ = i * 8;	// R
					*ptr++ = 0;	// G
					*ptr++ = 0;	// B
				}
			}
			for (int i = 0; i < 32; i++)
			{
				for (int j = 0; j < 256; j++)
				{
					*ptr++ = 0;	// R
					*ptr++ = i * 8;	// G
					*ptr++ = 0;	// B
				}
			}
			for (int i = 0; i < 32; i++)
			{
				for (int j = 0; j < 256; j++)
				{
					*ptr++ = 0;	// R
					*ptr++ = 0;	// G
					*ptr++ = i * 8;	// B
				}
			}
			for (int i = 0; i < 32; i++)
			{
				for (int j = 0; j < 256; j++)
				{
					*ptr++ = i * 8;	// R
					*ptr++ = i * 8;	// G
					*ptr++ = i * 8;	// B
				}
			}
			for (int i = 0; i < 128; i++)
			{
				for (int j = 0; j < 256; j++)
				{
					*ptr++ = i * 4;	// R
					*ptr++ = 255 - (i * 4);	// G
					*ptr++ = j;	// B
				}
			}
			DPImage *image = new DPImage(256, 256, 24, data);
			DatapointValue img(image);
			return Reading(conf->getValue("asset"), new Datapoint("testcard", img));
			}
		default:
			Logger::getLogger()->error("Unsupported depth %d", depth);
	}
}

/**
 * Reconfigure the plugin
 */
void plugin_reconfigure(PLUGIN_HANDLE *handle, string& newConfig)
{
ConfigCategory	*config = new ConfigCategory("testcard", newConfig);

	*handle = config;
}

/**
 * Shutdown the plugin
 */
void plugin_shutdown(PLUGIN_HANDLE *handle)
{
}

/**
 * Control entry point for a write operation.
 *
 * No write operations are currently supported by the camera
 */
bool plugin_write(PLUGIN_HANDLE *handle, string& name, string& value)
{

	return false;
}

/**
 * Control operation entry point. Currently only one operation
 * is supported by the camera, the trigger operation.
 */
bool plugin_operation(PLUGIN_HANDLE *handle, string& operation, int count, PLUGIN_PARAMETER **params)
{
	return false;
}
};
