/*
 * Fledge filter pipeline class for sending process
 *
 * Copyright (c) 2019 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Amandeep Singh Arora
 */

#include <north_filter_pipeline.h>
#include <sending.h>

#define JSON_CONFIG_FILTER_ELEM "filter"
#define JSON_CONFIG_PIPELINE_ELEM "pipeline"

using namespace std;

/**
 * NorthFilterPipeline class constructor
 *
 * This class abstracts the filter pipeline interface for sending process
 *
 * @param mgtClient	Management client handle
 * @param storage	Storage client handle
 * @param serviceName	Name of the service to which this pipeline applies
 */
NorthFilterPipeline::NorthFilterPipeline(ManagementClient* mgtClient, StorageClient& storage, string serviceName) : 
			FilterPipeline(mgtClient, storage, serviceName)
{
}

/**
 * Set the filter pipeline for sending process
 * 
 * This method calls the the method "plugin_init" for all loadad filters.
 * Up to date filter configurations and Ingest filtering methods
 * are passed to "plugin_init"
 *
 * @param passToOnwardFilter	Ptr to function that passes data to next filter
 * @param useFilteredData	Ptr to function that gets final filtered data
 * @param _sendingProcess	The SendingProcess class handle
 * @return 		True on success,
 *			False otherwise.
 * @thown		Any caught exception
 */
bool NorthFilterPipeline::setupFiltersPipeline(void *passToOnwardFilter, void *useFilteredData, void *_sendingProcess)
{
	bool initErrors = false;
	string errMsg = "'plugin_init' failed for filter '";
	for (auto it = m_filters.begin(); it != m_filters.end(); ++it)
	{
		string filterCategoryName =  serviceName + "_" + (*it)->getName();
		ConfigCategory updatedCfg;
		vector<string> children;
		
		try
		{
			Logger::getLogger()->info("Load plugin categoryName %s", filterCategoryName.c_str());
			// Fetch up to date filter configuration
			updatedCfg = mgtClient->getCategory(filterCategoryName);

			// Add filter category name under service/process config name
			children.push_back(filterCategoryName);
			mgtClient->addChildCategories(serviceName, children);
			
			m_filterCategories[filterCategoryName] = (*it);
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
			// Set load buffer index pointer as OUTPUT_HANDLE
			SendingProcess *sendingProcess = (SendingProcess *) _sendingProcess;
			const unsigned long* bufferIndex = sendingProcess->getLoadBufferIndexPtr();
			
			// Set the Ingest class pointer as OUTPUT_HANDLE
			if (!(*it)->init(updatedCfg,
					 (OUTPUT_HANDLE *)(bufferIndex),
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

	// Set filter pipeline is ready for data ingest
	m_ready = true;

	//Success
	return true;
}

