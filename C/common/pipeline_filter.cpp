/*
 * Fledge pipeline filter class
 *
 * Copyright (c) 2024 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <pipeline_element.h>
#include <filter_pipeline.h>
#include <config_handler.h>
#include <service_handler.h>
#include "rapidjson/writer.h"
#include "rapidjson/stringbuffer.h"

using namespace std;


/**
 * Construct the PipelineFilter class. This is the
 * specialisation of the PipelineElement that represents
 * a running filter in the pipeline.
 */
PipelineFilter::PipelineFilter(const string& name, const ConfigCategory& filterDetails) :
	PipelineElement(), m_name(name), m_plugin(NULL)
{
	m_name = name;
	if (!filterDetails.itemExists("plugin"))
	{
		string errMsg("loadFilters: 'plugin' item not found ");
		errMsg += "in " + m_name + " category";
		Logger::getLogger()->fatal(errMsg.c_str());
		throw runtime_error(errMsg);
	}
	m_pluginName = filterDetails.getValue("plugin");
	// Load filter plugin only: we don't call any plugin method right now
	m_handle = loadFilterPlugin(m_pluginName);
	if (!m_handle)
	{
		string errMsg("Cannot load filter plugin '" + m_pluginName + "'");
		Logger::getLogger()->fatal(errMsg.c_str());
		throw runtime_error(errMsg);
	}
}

PipelineFilter::~PipelineFilter()
{
	delete m_plugin;
}

/**
 * Setup the configuration for a filter in a pipeline
 *
 * @param	mgtClient	The managament client
 * @param	children	A vector to fill with child configuration categories
 */
bool PipelineFilter::setupConfiguration(ManagementClient *mgtClient, vector<string>& children)
{
	PluginManager *manager = PluginManager::getInstance();
	string filterConfig = manager->getInfo(m_handle)->config;

	m_categoryName = m_serviceName + "_" + m_name;
	// Create/Update default filter category items
	DefaultConfigCategory filterDefConfig(m_categoryName, filterConfig);
	string filterDescription = "Configuration of '" + m_name;
	filterDescription += "' filter for plugin '" + m_pluginName + "'";
	filterDefConfig.setDescription(filterDescription);

	if (!mgtClient->addCategory(filterDefConfig, true))
	{
		string errMsg("Cannot create/update '" + \
			      m_categoryName + "' filter category");
		Logger::getLogger()->fatal(errMsg.c_str());
		return false;
	}
	children.push_back(m_serviceName + '_' + m_name);

	// Instantiate the FilterPlugin class
	// in order to call plugin entry points
	m_plugin = new FilterPlugin(m_name, m_handle);
	if (!m_plugin)
		return false;
	return true;
}


/**
 * Load the specified filter plugin
 *
 * @param filterName	The filter plugin to load
 * @return		Plugin handle on success, NULL otherwise 
 *
 */
PLUGIN_HANDLE PipelineFilter::loadFilterPlugin(const string& filterName)
{
	if (filterName.empty())
	{
		Logger::getLogger()->error("Unable to fetch filter plugin '%s' from configuration.",
			filterName.c_str());
		// Failure
		return NULL;
	}
	Logger::getLogger()->info("Loading filter plugin '%s'.", filterName.c_str());

	PluginManager *manager = PluginManager::getInstance();
	PLUGIN_HANDLE handle;
	if ((handle = manager->loadPlugin(filterName, PLUGIN_TYPE_FILTER)) != NULL)
	{
		// Suceess
		Logger::getLogger()->info("Loaded filter plugin '%s'.", filterName.c_str());
	}
	return handle;
}

/**
 * Setup the configuration categories for the filter 
 * element in a pipeline
 *
 * @param mgmt	The Management client
 * @param ingest	The service handler for our service
 * @param filterCatiegories	A map of the category name to pipeline element
 */
bool PipelineFilter::setup(ManagementClient *mgmt, void *ingest, map<string, PipelineElement *>& filterCategories)
{
vector<string> children;

	Logger::getLogger()->info("Load plugin categoryName %s for %s", m_categoryName.c_str(), m_name.c_str());
	// Fetch up to date filter configuration
	m_updatedCfg = mgmt->getCategory(m_categoryName);

	// Pass Management client IP:Port to filter so that it may connect to bucket service
	m_updatedCfg.addItem("mgmt_client_url_base", "Management client host and port",
									"string", "127.0.0.1:0",
									mgmt->getUrlbase());

	// Add filter category name under service/process config name
	children.push_back(m_categoryName);
	mgmt->addChildCategories(m_serviceName, children);
		
	ConfigHandler *configHandler = ConfigHandler::getInstance(mgmt);
	configHandler->registerCategory((ServiceHandler *)ingest, m_categoryName);
	filterCategories[m_categoryName] = this;

	return true;
}

/**
 * Initialise the pipeline filter ready for ingest of data
 *
 * @param outHandle	The pipeline element we are sending the data to
 * @param output	
 */
bool PipelineFilter::init(OUTPUT_HANDLE* outHandle, OUTPUT_STREAM output)
{
	m_plugin->init(m_updatedCfg, outHandle, output);
	if (m_plugin->persistData())
	{
		// Plugin support SP_PERSIST_DATA
		// Instantiate the PluginData class
		m_plugin->m_plugin_data = new PluginData(m_storage);
		// Load plugin data from storage layer
		string pluginStoredData = m_plugin->m_plugin_data->loadStoredData(m_serviceName + m_name);
		//call 'plugin_start' with plugin data: startData()
		m_plugin->startData(pluginStoredData);
	}
	return true;
}

/**
 * Shutdown a pipeline element that is a filter.
 *
 * Remove registration for categories of interest, persist and plugin
 * data that needs persisting and call shutdown on the plugin itself.
 *
 * @param	serviceHandler The service handler of the service that is hostign the pipeline
 * @param	configHandler	The config handler for the service from which we unregister
 */
void PipelineFilter::shutdown(ServiceHandler *serviceHandler, ConfigHandler *configHandler)
{
	string filterCategoryName =  m_serviceName + "_" + m_name;
	configHandler->unregisterCategory(serviceHandler, filterCategoryName);
		
	// If plugin has SP_PERSIST_DATA option:
	if (m_plugin->m_plugin_data)
 	{
			// 1- call shutdownSaveData and get up-to-date plugin data.
			string saveData = m_plugin->shutdownSaveData();
			// 2- store returned data: key is service/task categoryName + pluginName
			string key(m_categoryName + m_plugin->getName());
			if (!m_plugin->m_plugin_data->persistPluginData(key, saveData))
			{
				Logger::getLogger()->error("Filter plugin %s has failed to save data [%s] for key %s",
							   m_plugin->getName().c_str(),
							   saveData.c_str(),
							   key.c_str());
			}
		}
		else
		{
			// Call filter plugin shutdown
			m_plugin->shutdown();
		}
}

/**
 * Reconfigure method
 */
void PipelineFilter::reconfigure(const string& newConfig)
{
	m_plugin->reconfigure(newConfig);
}
