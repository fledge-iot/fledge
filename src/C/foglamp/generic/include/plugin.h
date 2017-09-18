#ifndef _PLUGIN_H
#define _PLUGIN_H

#include <plugin_api.h>

/**
 * A generic representation of a plugin
 */
class Plugin {

  public:
    Plugin(PLUGIN_HANDLE handle);
    ~Plugin();

    string info();

  protected:
    PLUGIN_HANDLE handle;

  private:
}

#endif
