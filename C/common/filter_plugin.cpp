/*
 * FogLAMP plugin filter class
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Massimiliano Pinto
 */

#include <filter_plugin.h>
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
FilterPlugin::FilterPlugin(const std::string& name,
			   PLUGIN_HANDLE handle) : Plugin(handle), m_name(name)
{
	// Setup the function pointers to the plugin
	pluginInit = (PLUGIN_HANDLE (*)(const ConfigCategory *,
					OUTPUT_HANDLE *,
					OUTPUT_STREAM output))
					manager->resolveSymbol(handle,
							       "plugin_init");
  	pluginShutdownPtr = (void (*)(PLUGIN_HANDLE))
				      manager->resolveSymbol(handle,
							     "plugin_shutdown");
  	pluginIngestPtr = (void (*)(PLUGIN_HANDLE, READINGSET *))
				      manager->resolveSymbol(handle,
							     "plugin_ingest");
}

/**
 * FilterPlugin destructor
 */
FilterPlugin::~FilterPlugin()
{
}

/**
 * Call the loaded plugin "plugin_init" method
 *
 * @param config	The filter configuration
 * @param outHandle	The ouutput_handled passed with
 *			filtered data to OUTPUT_STREAM function
 * @param outputFunc	The output_stream function pointer
 * 			the filter uses to pass data out
 * @return		The PLUGIN_HANDLE object
 */
PLUGIN_HANDLE FilterPlugin::init(const ConfigCategory& config,
				 OUTPUT_HANDLE *outHandle,
				 OUTPUT_STREAM outputFunc)
{
	m_instance = this->pluginInit(&config,
				      outHandle,
				      outputFunc);
	return (m_instance ? &m_instance : NULL);
}

/**
 * Call the loaded plugin "plugin_shutdown" method
 */
void FilterPlugin::shutdown()
{
	return this->pluginShutdownPtr(m_instance);
}

/**
 * Call the loaded plugin "plugin_ingest" method
 *
 * This call ingest the readings through the filters chain
 */
void FilterPlugin::ingest(READINGSET* readings)
{
        return this->pluginIngestPtr(m_instance, readings);
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
PLUGIN_HANDLE FilterPlugin::loadFilterPlugin(const string& filterName)
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
 * Cleanup all the load filters setup
 *
 * Call "plugin_shutdown" method and free the FilterPlugin object
 *
 * Static method
 *
 * @param loadedFilters		The vector of loaded filters
 *
 */
void FilterPlugin::cleanupFilters(std::vector<FilterPlugin *>& loadedFilters)
{
	// Cleanup filters
	for (auto it = loadedFilters.begin(); it != loadedFilters.end(); ++it)
	{
		// Call filter plugin shutdown
		(*it)->shutdown();
		// Free filter
		delete *it;
	}
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
bool FilterPlugin::loadFilters(const string& categoryName,
			       std::vector<FilterPlugin *>& filters,
			       ManagementClient* manager)
{
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
					string filterName = itr->GetString();
					PLUGIN_HANDLE filterHandle;
					// Load filter plugin only: we don't call any plugin method right now
					filterHandle = FilterPlugin::loadFilterPlugin(filterName);
					if (!filterHandle)
					{
						string errMsg("Cannot load filter plugin '" + filterName + "'");
						Logger::getLogger()->fatal(errMsg.c_str());
						throw runtime_error(errMsg);
					}
					else
					{
						// Save filter handler
						filterInfo.push_back(pair<string,PLUGIN_HANDLE>
								     (filterName, filterHandle));
					}
				}

				// We have kept filter default config in the filterInfo map
				// Handle configuration for each filter
				PluginManager *pluginManager = PluginManager::getInstance();
				for (vector<pair<string, PLUGIN_HANDLE>>::iterator itr = filterInfo.begin();
				     itr != filterInfo.end();
				     ++itr)
				{
					// Create/Update valid load filter categories only
					string filterCategoryName = categoryName;
					filterCategoryName.append("_");
					filterCategoryName += itr->first;
					filterCategoryName.append("Filter");
					// Get plugin information
					string filterConfig = pluginManager->getInfo(itr->second)->config;

					// Create/Update filter category
					DefaultConfigCategory filterDefConfig(filterCategoryName, filterConfig);
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
					filters.push_back(currentFilter);
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
