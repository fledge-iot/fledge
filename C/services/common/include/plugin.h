#ifndef _PLUGIN_H
#define _PLUGIN_H
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
    PLUGIN_INFORMATION *info;
};

#endif
