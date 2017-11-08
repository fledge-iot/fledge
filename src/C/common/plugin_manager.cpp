/*
 * FogLAMP storage service.
 *
 * Copyright (c) 2017 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <plugin_manager.h>
#include <cstdio>
#include <dlfcn.h>
#include <string.h>
#include <iostream>
#include <unistd.h>

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
PLUGIN_HANDLE hndl = NULL;
char          buf[128];

  if (pluginNames.find(name) != pluginNames.end())
  {
    if (type.compare(pluginTypes.find(name)->first))
    {
      logger->error("Plugin %s is already loaded but not the expected type %s\n",
        name.c_str(), type.c_str());
      return NULL;
    }
    return pluginNames[name];
  }

  /*
   * Find and load the dynamic library that is the plugin
   */
  snprintf(buf, sizeof(buf), "./lib%s.so", name.c_str());
  if (access(buf, F_OK) != 0)
  {
    char *home = getenv("FOGLAMP_HOME");
    if (home)
    {
        snprintf(buf, sizeof(buf), "%s/plugins/lib%s.so", home, name.c_str());
    }
  }
  if ((hndl = dlopen(buf, RTLD_LAZY)) != NULL)
  {
    func_t infoEntry = (func_t)dlsym(hndl, "plugin_info");
    if (infoEntry == NULL)
    {
      // Unable to find plugin_info entry point
      logger->error("Plugin %s does not support plugin_info entry point.\n", name.c_str());
      dlclose(hndl);
      return NULL;
    }
    PLUGIN_INFORMATION *info = (PLUGIN_INFORMATION *)(*infoEntry)();

    if (strcmp(info->type, type.c_str()) != 0)
    {
      // Log error, incorrect plugin type
      logger->error("Plugin %s is not of the expected type %s, it is of type %s.\n",
        name, type.c_str(), info->type);
      dlclose(hndl);
      return NULL;
    }

    plugins.push_back(hndl);
    pluginNames[name] = hndl;
    pluginTypes[name] = hndl;
    pluginInfo[hndl] = info;
  }
  else
  {
    logger->error("PluginManager: Failed to load plugin %s.", name.c_str());
  }

  return hndl;
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
void *PluginManager::resolveSymbol(PLUGIN_HANDLE handle, const string& symbol)
{
  return dlsym(handle, symbol.c_str());
}
