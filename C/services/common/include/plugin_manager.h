#ifndef PLUGIN_MANAGER_H
#define PLUGIN_MANAGER_H
/*
 * Fledge storage service.
 *
 * Copyright (c) 2017, 2018 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch, Massimiliano Pinto
 */

#include <plugin_api.h>
#include <plugin_handle.h>
#include <logger.h>
#include <string>
#include <list>
#include <map>
#include <vector>

typedef enum PluginType
{
	PLUGIN_TYPE_ID_STORAGE,
	PLUGIN_TYPE_ID_OTHER
} tPluginType;

enum PLUGIN_TYPE {
	BINARY_PLUGIN,
	PYTHON_PLUGIN,
	JSON_PLUGIN
};


/**
 * The manager for plugins.
 *
 * This manager is a singleton and is responsible for loading, tracking and unloading
 * the plugins within the system.
 */
class PluginManager {
	public:
		static PluginManager *getInstance();
		PLUGIN_HANDLE	loadPlugin(const std::string& name,
					   const std::string& type);
		void		unloadPlugin(PLUGIN_HANDLE handle);
		void*		resolveSymbol(PLUGIN_HANDLE handle,
					      const std::string& symbol);
		PLUGIN_HANDLE	findPluginByName(const std::string& name);
		PLUGIN_HANDLE	findPluginByType(const std::string& type);
		PLUGIN_INFORMATION
				*getInfo(const PLUGIN_HANDLE);
		void		getInstalledPlugins(const std::string& type,
						    std::list<std::string>& plugins);
		void setPluginType(tPluginType type);
		PLUGIN_TYPE getPluginImplType(const PLUGIN_HANDLE hndl) { return pluginImplTypes[hndl]; }
		std::vector<std::string> getPluginsByFlags(const std::string& type, unsigned int flags);
	public:
                static PluginManager* instance;

	private:
                PluginManager();
		std::string	findPlugin(std::string name, std::string _type, std::string _plugin_path, PLUGIN_TYPE type);

	private:
                std::list<PLUGIN_HANDLE>		plugins;
                std::map<std::string, PLUGIN_HANDLE>	pluginNames;
                std::map<std::string, std::string>	pluginTypes;
		std::map<PLUGIN_HANDLE, PLUGIN_TYPE>	pluginImplTypes;
                std::map<PLUGIN_HANDLE, PLUGIN_INFORMATION *>
							pluginInfo;
                std::map<PLUGIN_HANDLE, PluginHandle*>
							pluginHandleMap;
                Logger*					logger;
		tPluginType				m_pluginType;
};

#endif
