#ifndef PLUGIN_MANAGER_H
#define PLUGIN_MANAGER_H

#include <plugin_api.h>
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
};

#endif
