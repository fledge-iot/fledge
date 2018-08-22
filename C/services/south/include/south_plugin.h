#ifndef _SOUTH_PLUGIN
#define _SOUTH_PLUGIN
/*
 * FogLAMP south service.
 *
 * Copyright (c) 2018 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */

#include <plugin.h>
#include <plugin_manager.h>
#include <config_category.h>
#include <string>
#include <reading.h>

typedef void (*INGEST_CB)(void *, Reading);
/**
 * Class that represents a south plugin.
 *
 * The purpose of this class is to hide the use of the pointers into the
 * dynamically loaded plugin and wrap the interface into a class that
 * can be used directly in the south subsystem.
 *
 * This is achieved by having a set of private member variables which are
 * the pointers to the functions in the plugin, and a set of public methods
 * that will call these functions via the function pointers.
 */
class SouthPlugin : public Plugin {

public:
	SouthPlugin(PLUGIN_HANDLE handle, const ConfigCategory& category);
	~SouthPlugin();

	Reading		poll();
	void		start();
	void		reconfigure(std::string&);
	void		shutdown();
	void		registerIngest(INGEST_CB, void *);
	bool		isAsync() { return info->options & SP_ASYNC; };

private:
	PLUGIN_HANDLE	instance;
	void		(*pluginStartPtr)(PLUGIN_HANDLE);
	Reading		(*pluginPollPtr)(PLUGIN_HANDLE);
	void		(*pluginReconfigurePtr)(PLUGIN_HANDLE, std::string& newConfig);
	void		(*pluginShutdownPtr)(PLUGIN_HANDLE);
	void		(*pluginRegisterPtr)(PLUGIN_HANDLE, INGEST_CB, void *);
};

#endif
