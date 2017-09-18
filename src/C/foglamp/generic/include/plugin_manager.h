#ifndef PLUGIN_MANAGER_H
#define PLUGIN_MANAGER_H

#include <plugin_api.h>
#include <list>
#include <map>

/**
 * The manager for plugins.
 *
 * This manager is a singleton and is responsible for loading, trackign and unloading
 * the plugins within the system.
 */
class PluginManager {
	public:
                static PluginManager *getInstance();
        	PLUGIN_HANDLE loadPlugin(const string& name, const string& type);
		unloadPlugin(PLUGIN_HANDLE handle);
                findPluginByName(string name);
                findPluginByType(string type);

	private:
		list<PLUGIN_HANDLE>	        plugins;
                map<string, PLUGIN_HANDLE>      pluginNames;
                map<string, PLUGIN_HANDLE>      pluginTypes;
                map<string, PLUGIN_INFORMATION> pluginInfo;
                PluginManager                   *instance = 0;
                PluginManager();
}

#endif
