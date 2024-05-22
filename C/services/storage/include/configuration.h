#ifndef _CONFIGURATION_H
#define _CONFIGURATION_H
/*
 * Fledge storage service.
 *
 * Copyright (c) 2017 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */

#include <logger.h>
#include <string>
#include <rapidjson/document.h>
#include <config_category.h>

#define STORAGE_CATEGORY	  "Storage"
#define CATEGORY_DESCRIPTION	  "Storage configuration"
#define ADVANCED		  "Advanced"
#define CONFIGURATION_CACHE_FILE  "storage.json"

/**
 * The storage service must handle its own configuration differently
 * to other services as it is unable to read the configuration from
 * the database. The configuration is required in order to connnect
 * to the database. Therefore it keeps a shadow copy in a local file
 * and it keeps this local, cached copy up to date by registering
 * interest in the category and whenever a chaneg is made writing
 * the category to the local cache file.
 */
class StorageConfiguration {
  public:
    StorageConfiguration();
    ~StorageConfiguration();
    const char            *getValue(const std::string& key);
    bool		  hasValue(const std::string& key);
    bool                  setValue(const std::string& key, const std::string& value);
    void                  updateCategory(const std::string& json);
    DefaultConfigCategory *getDefaultCategory();
  private:
    void		  getConfigCache(std::string& cache);
    rapidjson::Document   *document;
    void                  readCache();
    void                  writeCache();
    void                  checkCache();
    void                  updateStoragePluginConfig();
    Logger *logger;
};

#endif
