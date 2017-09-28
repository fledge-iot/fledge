#ifndef _STORAGE_SERVICE_H
#define _STORAGE_SERVICE_H
/*
 * FogLAMP storage service.
 *
 * Copyright (c) 2017 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */

#include <storage_api.h>
#include <logger.h>
#include <configuration.h>
#include <storage_plugin.h>

#define SERVICE_NAME  "FogLAMP Storage"

class StorageService {
  public:
    StorageService();
    void start();
    void stop();
  private:
    bool loadPlugin();
    StorageApi    *api;
    StorageConfiguration *config;
    Logger        *logger;
    StoragePlugin *storagePlugin;
};
#endif
