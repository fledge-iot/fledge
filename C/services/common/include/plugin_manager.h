#ifndef PLUGIN_MANAGER_H
#define PLUGIN_MANAGER_H
/*
 * FogLAMP storage service.
 *
 * Copyright (c) 2017 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */

#include <plugin_api.h>
#include <logger.h>
#include <string>
#include <list>
#include <map>

/**
 * The manager for plugins.
 *
 * This manager is a singleton and is responsible for loading, tracking and unloading
 * the plugins within the system.
 */
class PluginManager {
	public:
                static PluginManager *getInstance();
        	PLUGIN_HANDLE loadPlugin(const std::string& name, const std::string& type);
		void unloadPlugin(PLUGIN_HANDLE handle);
    void *resolveSymbol(PLUGIN_HANDLE handle, const std::string& symbol);
                PLUGIN_HANDLE findPluginByName(const std::string& name);
                PLUGIN_HANDLE findPluginByType(const std::string& type);
                PLUGIN_INFORMATION *getInfo(const PLUGIN_HANDLE);
                static PluginManager            *instance;

	private:
                std::list<PLUGIN_HANDLE>	        plugins;
                std::map<std::string, PLUGIN_HANDLE>      pluginNames;
                std::map<std::string, PLUGIN_HANDLE>      pluginTypes;
                std::map<PLUGIN_HANDLE, PLUGIN_INFORMATION *> pluginInfo;
                PluginManager();
                Logger      *logger;
};

#endif
