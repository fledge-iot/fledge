#include <plugin_manager.h>
#include <cstdio>
#include <dlfcn.h>
#include <string.h>

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
      return NULL;
    }
    return pluginNames[name];
  }

  /*
   * Find and load the dynamic library that is the plugin
   */
  snprintf(buf, sizeof(buf), "lib%s.so", name.c_str());
  if ((hndl = dlopen(buf, RTLD_LAZY)) != NULL)
  {
    func_t infoEntry = (func_t)dlsym(hndl, "plugin_info");
    if (infoEntry == NULL)
    {
      // Unable to find plugin_info entry point
      return NULL;
    }
    PLUGIN_INFORMATION *info = (PLUGIN_INFORMATION *)(*infoEntry)();

    if (strcmp(info->type, type.c_str()) != 0)
    {
      // Log error, incorrect plugin type
      dlclose(hndl);
      return NULL;
    }

    plugins.push_back(hndl);
    pluginNames[name] = hndl;
    pluginTypes[name] = hndl;
    pluginInfo[hndl] = info;
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
