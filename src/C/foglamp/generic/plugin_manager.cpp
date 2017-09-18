#include <plugin_manager.h>


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

  /*
   * Find and load the dynamic library that is the plugin
   */
  snprint(buf, sizeof(buf), "lib%s.so", name.c_str());
  if ((hndl = dlopen(buf, RTLD_LAZY)) != NULL)
  {
    void *infoEntry = dlsym(hndl, "plugin_info");
    if (infoEntry == NULL)
    {
      // Unable to find plugin_info entry point
      return NULL;
    }
    PLUGIN_INFORMATION *info = (PLUGIN_INFORMATION *)(*infoEntry)();
  }

  return hndl;
}
