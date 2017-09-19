#ifndef _PLUGIN_H
#define _PLUGIN_H

#include <plugin_api.h>

class PluginManager;

/**
 * A generic representation of a plugin
 */
class Plugin {

  public:
    Plugin(PLUGIN_HANDLE handle);
    ~Plugin();

    const PLUGIN_INFORMATION *getInfo();

  protected:
    PLUGIN_HANDLE handle;
    PluginManager *manager;

  private:
    PLUGIN_INFORMATION *info;
};

#endif
