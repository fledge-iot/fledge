/*
 * FogLAMP plugin filter class
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Massimiliano Pinto
 */

#include <filter_pipeline.h>
#include "rapidjson/writer.h"
#include "rapidjson/stringbuffer.h"

#define JSON_CONFIG_FILTER_ELEM "filter"
#define JSON_CONFIG_PIPELINE_ELEM "pipeline"

using namespace std;

/**
 * FilterPlugin class constructor
 *
 * This class wraps the filter plugin C interface and creates
 * set of function pointers that resolve to the loaded plugin and
 * enclose in the class.
 *
 * @param name		The filter name
 * @param handle	The loaded plugin handle
 *
 * Set the function pointers to Filter Plugin C API
 */
FilterPipeline::FilterPipeline()
{
}

/**
 * FilterPlugin destructor
 */
FilterPipeline::~FilterPipeline()
{
}

/**
 * Load the specified filter plugin
 *
 * Static method
 *
 * @param    filterName		The filter plugin to load
 * @return   			Plugin handle on success, NULL otherwise 
 *
 */
PLUGIN_HANDLE FilterPipeline::loadFilterPlugin(const string& filterName)
{
	if (filterName.empty())
	{
		Logger::getLogger()->error("Unable to fetch filter plugin '%s' from configuration.",
			filterName.c_str());
		// Failure
		return NULL;
	}
	Logger::getLogger()->info("Loading filter plugin '%s'.", filterName.c_str());

	PluginManager* manager = PluginManager::getInstance();
	PLUGIN_HANDLE handle;
	if ((handle = manager->loadPlugin(filterName, PLUGIN_TYPE_FILTER)) != NULL)
	{
		// Suceess
		Logger::getLogger()->info("Loaded filter plugin '%s'.", filterName.c_str());
	}
	return handle;
}

/**
 * Load all filter plugins found in the configuration category
 *
 * Static method
 *
 * @param categoryName	Configuration category
 * @param filters	Vector of FilterPlugin to be filled
 * @param manager	The management client
 * @return		True if filters are loaded (or no filters at all)
 *			False otherwise
 */
bool FilterPipeline::loadFilters(const string& categoryName, ManagementClient* manager)
{
		//PluginManager* manager = PluginManager::getInstance();
        try
        {
        	// Get the category with values and defaults
        	ConfigCategory config = manager->getCategory(categoryName);
                string filter = config.getValue(JSON_CONFIG_FILTER_ELEM);
                if (!filter.empty())
                {
			std::vector<pair<string, PLUGIN_HANDLE>> filterInfo;

			// Remove \" and leading/trailing "
			// TODO: improve/change this
			filter.erase(remove(filter.begin(), filter.end(), '\\' ), filter.end());
			size_t i;
			while (! (i = filter.find('"')) || (i = filter.rfind('"')) == static_cast<unsigned char>(filter.size() - 1))
			{
				filter.erase(i, 1);
			}

			//Parse JSON object for filters
			Document theFilters;
			theFilters.Parse(filter.c_str());
			// The "pipeline" property must be an array
			if (theFilters.HasParseError() ||
				!theFilters.HasMember(JSON_CONFIG_PIPELINE_ELEM) ||
				!theFilters[JSON_CONFIG_PIPELINE_ELEM].IsArray())
			{
				string errMsg("loadFilters: can not parse JSON '");
				errMsg += string(JSON_CONFIG_FILTER_ELEM) + "' property";
				Logger::getLogger()->fatal(errMsg.c_str());
				throw runtime_error(errMsg);
			}
			else
			{
				const Value& filterList = theFilters[JSON_CONFIG_PIPELINE_ELEM];
				if (!filterList.Size())
				{
					// Empty array, just return true
					return true;
				}

				// Prepare printable list of filters
				StringBuffer buffer;
				Writer<StringBuffer> writer(buffer);
				filterList.Accept(writer);
				string printableList(buffer.GetString());

				string logMsg("loadFilters: found filter(s) ");
				logMsg += printableList + " for plugin '";
				logMsg += categoryName + "'";

				Logger::getLogger()->info(logMsg.c_str());

				// Try loading all filter plugins: abort on any error
				for (Value::ConstValueIterator itr = filterList.Begin(); itr != filterList.End(); ++itr)
				{
					// Get "plugin" item fromn filterCategoryName
					string filterCategoryName = itr->GetString();
					ConfigCategory filterDetails = manager->getCategory(filterCategoryName);
					if (!filterDetails.itemExists("plugin"))
					{
						string errMsg("loadFilters: 'plugin' item not found ");
						errMsg += "in " + filterCategoryName + " category";
						Logger::getLogger()->fatal(errMsg.c_str());
						throw runtime_error(errMsg);
					}
					string filterName = filterDetails.getValue("plugin");
					PLUGIN_HANDLE filterHandle;
					// Load filter plugin only: we don't call any plugin method right now
					filterHandle = loadFilterPlugin(filterName);
					if (!filterHandle)
					{
						string errMsg("Cannot load filter plugin '" + filterName + "'");
						Logger::getLogger()->fatal(errMsg.c_str());
						throw runtime_error(errMsg);
					}
					else
					{
						// Save filter handler: key is filterCategoryName
						filterInfo.push_back(pair<string,PLUGIN_HANDLE>
								     (filterCategoryName, filterHandle));
					}
				}

				// We have kept filter default config in the filterInfo map
				// Handle configuration for each filter
				PluginManager *pluginManager = PluginManager::getInstance();
				for (vector<pair<string, PLUGIN_HANDLE>>::iterator itr = filterInfo.begin();
				     itr != filterInfo.end();
				     ++itr)
				{
					// Get plugin default configuration
					string filterConfig = pluginManager->getInfo(itr->second)->config;

					// Update filter category items
					DefaultConfigCategory filterDefConfig(itr->first, filterConfig);
					string filterDescription = "Configuration of '" + itr->first;
					filterDescription += "' filter for plugin '" + categoryName + "'";
					filterDefConfig.setDescription(filterDescription);

					if (!manager->addCategory(filterDefConfig, true))
					{
						string errMsg("Cannot create/update '" + \
							      categoryName + "' filter category");
						Logger::getLogger()->fatal(errMsg.c_str());
						throw runtime_error(errMsg);
					}

					// Instantiate the FilterPlugin class
					// in order to call plugin entry points
					FilterPlugin* currentFilter = new FilterPlugin(itr->first,
										       itr->second);

					// Add filter to filters vector
					m_filters.push_back(currentFilter);
				}
			}
		}
		return true;
	}
	catch (ConfigItemNotFound* e)
	{
		delete e;
		Logger::getLogger()->info("loadFilters: no filters configured for '" + categoryName + "'");
		return true;
	}
	catch (exception& e)
	{
		Logger::getLogger()->fatal("loadFilters: failed to handle '" + categoryName + "' filters.");
		return false;
	}
	catch (...)
	{
		Logger::getLogger()->fatal("loadFilters: generic exception while loading '" + categoryName + "' filters.");
		return false;
	}
}

/**
 * Set the filter pipeline
 * 
 * This method calls the the method "plugin_init" for all loadade filters.
 * Up to date filter configurations and Ingest filtering methods
 * are passed to "plugin_init"
 *
 * @param ingest	The ingest class
 * @return 		True on success,
 *			False otherwise.
 * @thown		Any caught exception
 */
bool FilterPipeline::setupFiltersPipeline(ManagementClient* mgtClient, StorageClient& storage, string serviceName,
						void *passToOnwardFilter, void *useFilteredData) const
{
	bool initErrors = false;
	string errMsg = "'plugin_init' failed for filter '";
	for (auto it = m_filters.begin(); it != m_filters.end(); ++it)
	{
		string filterCategoryName = (*it)->getName();
		ConfigCategory updatedCfg;
		vector<string> children;
        
		try
		{
			// Fetch up to date filter configuration
			updatedCfg = mgtClient->getCategory(filterCategoryName);

			// Add filter category name under service/process config name
			children.push_back(filterCategoryName);
			mgtClient->addChildCategories(serviceName, children);
		}
		// TODO catch specific exceptions
		catch (...)
		{       
			throw;      
		}                   

		// Iterate the load filters set in the Ingest class m_filters member 
		if ((it + 1) != m_filters.end())
		{
			// Set next filter pointer as OUTPUT_HANDLE
			if (!(*it)->init(updatedCfg,
				    (OUTPUT_HANDLE *)(*(it + 1)),
				    filterReadingSetFn(passToOnwardFilter)))
			{
				errMsg += (*it)->getName() + "'";
				initErrors = true;
				break;
			}
		}
		else
		{
			// Set the Ingest class pointer as OUTPUT_HANDLE
			if (!(*it)->init(updatedCfg,
					 (OUTPUT_HANDLE *)this,
					 filterReadingSetFn(useFilteredData)))
			{
				errMsg += (*it)->getName() + "'";
				initErrors = true;
				break;
			}
		}

		if ((*it)->persistData())
		{
			// Plugin support SP_PERSIST_DATA
			// Instantiate the PluginData class
			(*it)->m_plugin_data = new PluginData(&storage);
			// Load plugin data from storage layer
			string pluginStoredData = (*it)->m_plugin_data->loadStoredData(serviceName + (*it)->getName());
 			//call 'plugin_start' with plugin data: startData()
			(*it)->startData(pluginStoredData);
		}
		else
		{
			// We don't call simple plugin_start for filters right now
		}
	}

	if (initErrors)
	{
		// Failure
		Logger::getLogger()->fatal("%s error: %s", __FUNCTION__, errMsg.c_str());
		return false;
	}

	//Success
	return true;
}

/**
 * Cleanup all the load filters setup
 *
 * Call "plugin_shutdown" method and free the FilterPlugin object
 *
 * Static method
 *
 * @param loadedFilters		The vector of loaded filters
 * @param categoryName		Configuration category
 *
 */
void FilterPipeline::cleanupFilters(const string& categoryName)
{
	// Cleanup filters
	for (auto it = m_filters.begin(); it != m_filters.end(); ++it)
	{
		FilterPlugin* filter = *it;
		// If plugin has SP_PERSIST_DATA option:
		if (filter->m_plugin_data)
	 	{
			// 1- call shutdownSaveData and get up-to-date plugin data.
			string saveData = filter->shutdownSaveData();
			// 2- store returned data: key is service/task categoryName + pluginName
			string key(categoryName + filter->getName());
			if (!filter->m_plugin_data->persistPluginData(key, saveData))
			{
				Logger::getLogger()->error("Filter plugin %s has failed to save data [%s] for key %s",
							   filter->getName().c_str(),
							   saveData.c_str(),
							   key.c_str());
			}
		}
		else
		{
			// Call filter plugin shutdown
			(*it)->shutdown();
		}

		// Free filter
		delete *it;
	}
}

