/*
 * FogLAMP plugin manager.
 *
 * Copyright (c) 2017, 2018 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch, Massimiliano Pinto
 */
#include <cstdio>
#include <dlfcn.h>
#include <string.h>
#include <iostream>
#include <unistd.h>
#include <plugin_manager.h>
#include <binary_plugin_handle.h>
#include <python_plugin_handle.h>
#include <dirent.h>

using namespace std;

PluginManager *PluginManager::instance = 0;

typedef PLUGIN_INFORMATION *(*func_t)();

/**
 * PluginManager Singleton implementation
*/
PluginManager *PluginManager::getInstance()
{
  if (!instance)
    instance = new PluginManager();
  return instance;
}

/**
 * Plugin Manager Constructor
 */
PluginManager::PluginManager()
{
  logger = Logger::getLogger();
}

/**
 * Load a given plugin
 */
PLUGIN_HANDLE PluginManager::loadPlugin(const string& name, const string& type)
{
PluginHandle *pluginHandle = NULL;
PLUGIN_HANDLE hndl;
char          buf[128];

  if (pluginNames.find(name) != pluginNames.end())
  {
    if (type.compare(pluginTypes.find(name)->second))
    {
      logger->error("Plugin %s is already loaded but not the expected type %s\n",
        name.c_str(), type.c_str());
      return NULL;
    }
    return pluginNames[name];
  }

  char *home = getenv("FOGLAMP_ROOT");

  /*
   * Find and try to load the dynamic library that is the plugin
   */
  snprintf(buf, sizeof(buf), "./lib%s.so", name.c_str());
  if (access(buf, F_OK) != 0 && home)
  {
	snprintf(buf,
	         sizeof(buf),
	         "%s/plugins/%s/%s/lib%s.so",
	         home,
	         type.c_str(),
	         name.c_str(),
	         name.c_str());
  }
  if (access(buf, F_OK|R_OK) == 0)
  {
	pluginHandle = new BinaryPluginHandle(name.c_str(), buf);
	hndl = pluginHandle->getHandle();
    if (hndl != NULL)
    {
      func_t infoEntry = (func_t)pluginHandle->GetInfo();
      if (infoEntry == NULL)
      {
        // Unable to find plugin_info entry point
        logger->error("C plugin %s does not support plugin_info entry point.\n", name.c_str());
        delete pluginHandle;
        return NULL;
      }
      PLUGIN_INFORMATION *info = (PLUGIN_INFORMATION *)(*infoEntry)();

	    logger->debug("%s:%d: name=%s, type=%s, default config=%s", __FUNCTION__, __LINE__, info->name, info->type, info->config);
	  
      if (strcmp(info->type, type.c_str()) != 0)
      {
        // Log error, incorrect plugin type
        logger->error("C plugin %s is not of the expected type %s, it is of type %s.\n",
          name.c_str(), type.c_str(), info->type);
        delete pluginHandle;
        return NULL;
      }
	  
      plugins.push_back(pluginHandle);
      pluginNames[name] = hndl;
      pluginTypes[name] = type;
      pluginInfo[hndl] = info;

      pluginHandleMap[hndl] = pluginHandle;
	    logger->debug("%s:%d: Added entry in pluginHandleMap={%p, %p}", __FUNCTION__, __LINE__, hndl, pluginHandle);
    }
    else
    {
		logger->error("PluginManager: Failed to load C plugin %s in %s: %s.",
                    name.c_str(),
                    buf,
                    dlerror());
    }
    return hndl;
  }

  // look for and load python plugin with given name
  snprintf(buf,
             sizeof(buf),
             "%s/python/foglamp/plugins/%s/%s/%s.py",
             home,
             type.c_str(),
             name.c_str(),
             name.c_str());
    
  if (access(buf, F_OK|R_OK) == 0)
  {
	pluginHandle = new PythonPluginHandle(name.c_str(), buf);
	hndl = pluginHandle->getHandle();
    if (hndl != NULL)
    {
      func_t infoEntry = (func_t)pluginHandle->GetInfo();
      if (infoEntry == NULL)
      {
        // Unable to find plugin_info entry point
        logger->error("Python plugin %s does not support plugin_info entry point.\n", name.c_str());
        delete pluginHandle;
        return NULL;
      }
      PLUGIN_INFORMATION *info = (PLUGIN_INFORMATION *)(*infoEntry)();
	  
      if (strcmp(info->type, type.c_str()) != 0)
      {
        // Log error, incorrect plugin type
        logger->error("C plugin %s is not of the expected type %s, it is of type %s.\n",
          name.c_str(), type.c_str(), info->type);
        delete pluginHandle;
        return NULL;
      }
      plugins.push_back(pluginHandle);
      pluginNames[name] = hndl;
      pluginTypes[name] = type;
      pluginInfo[hndl] = info;
      pluginHandleMap[hndl] = pluginHandle;
    }
    else
    {
      logger->error("PluginManager: Failed to load python plugin %s in %s",
                    name.c_str(),
                    buf);
    }
    return hndl;
  }
  logger->error("PluginManager: Failed to load C/python plugin '%s' ", name.c_str());
  return NULL;
}

/**
 * Find a loaded plugin by name.
 */
PLUGIN_HANDLE PluginManager::findPluginByName(const string& name)
{
  if (pluginNames.find(name) == pluginNames.end())
  {
    return NULL;
  }
  return pluginNames.find(name)->second;
}

/**
 * Find a loaded plugin by type
 */
PLUGIN_HANDLE PluginManager::findPluginByType(const string& type)
{
  if (pluginNames.find(type) == pluginNames.end())
  {
    return NULL;
  }
  return pluginNames.find(type)->second;
}

/**
 * Return the information for a named plugin
 */
PLUGIN_INFORMATION *PluginManager::getInfo(const PLUGIN_HANDLE handle)
{
  if (pluginInfo.find(handle) == pluginInfo.end())
  {
    return NULL;
  }
  return pluginInfo.find(handle)->second;
}

/**
 * Resolve a symbol within the plugin
 */
PLUGIN_HANDLE PluginManager::resolveSymbol(PLUGIN_HANDLE handle, const string& symbol)
{
  if (pluginHandleMap.find(handle) == pluginHandleMap.end())
  {
  	logger->warn("%s:%d: Cannot find PLUGIN_HANDLE in pluginHandleMap: returning NULL", __FUNCTION__, __LINE__);
    return NULL;
  }
  return pluginHandleMap.find(handle)->second->ResolveSymbol(symbol.c_str());
}

/**
 * Get the installed plugins in the given plugin type
 * subdirectory of "plugins" under FOGLAMP_ROOT
 * Plugin type is one of:
 * south, north, filter, notificationRule, notificationDelivery
 *
 * @param    type		The plugin type
 * @param    plugins		The output plugin list name to fill	
 */
void PluginManager::getInstalledPlugins(const string& type,
					list<string>& plugins)
{
	char *home = getenv("FOGLAMP_ROOT");
	if (home)
	{
		struct dirent *entry;
		DIR *dp;
		string path = home;
		path += "/plugins/" + type + "/";

		// Open the plugins dir/type
		dp = opendir(path.c_str());

		if (!dp)
		{
			// Can not open specified dir path
			char msg[128];
			char* ret = strerror_r(errno, msg, 128);
			logger->fatal("Can not access plugin directory %s: %s",
				      path.c_str(),
				      ret);
			return;
		}

		/**
		 * Get all sub directory names in path:
		 * path = plugins/filter/
		 *     delta
		 *     scale

		 * Plugin filename is libdelta.so, libscale.so
		 * Plugin name is the subdirecory name in path
		 */
		while ((entry = readdir(dp)))
		{
			if (strcmp (entry->d_name, "..") != 0 &&
			    strcmp (entry->d_name, ".") != 0)
			{
				// Load plugin, given its name: the directory name
				loadPlugin(entry->d_name, type);
				// Add name to ouput list
				plugins.push_back(entry->d_name);
			}
		}
		closedir(dp);
	}
}
