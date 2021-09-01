#ifndef _PLUGIN_CONFIGURATION_H
#define _PLUGIN_CONFIGURATION_H
/*
 * Fledge storage service.
 *
 * Copyright (c) 2020 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */

#include <logger.h>
#include <string>
#include <rapidjson/document.h>
#include <config_category.h>
#include <management_client.h>

class StoragePlugin;

/**
 * The storage service must handle its own configuration differently
 * to other services as it is unable to read the configuration from
 * the database.
 * This class deals with the configuration from the storage plugins, 
 * maintaining a cache for the plugin
 */
class StoragePluginConfiguration {
  public:
    StoragePluginConfiguration(const std::string& name, StoragePlugin *plugin);
    const char            *getValue(const std::string& key);
    bool		  hasValue(const std::string& key);
    bool                  setValue(const std::string& key, const std::string& value);
    void                  updateCategory(const std::string& json);
    void		  registerCategory(ManagementClient *client);
    DefaultConfigCategory *getDefaultCategory();
    ConfigCategory	  *getConfiguration();
  private:
    void		  getConfigCache(std::string& cache);
    void                  readCache();
    void                  writeCache();
    void		  updateCache();
    const std::string	  m_name;
    const StoragePlugin	  *m_plugin;
    std::string		  m_category;
    std::string	    	  m_defaultConfiguration;
    rapidjson::Document   *m_document;
    Logger                *m_logger;
};

#endif
