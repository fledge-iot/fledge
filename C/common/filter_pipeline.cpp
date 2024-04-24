/*
 * Fledge plugin filter class
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Amandeep Singh Arora
 */

#include <filter_pipeline.h>
#include <config_handler.h>
#include <service_handler.h>
#include "rapidjson/writer.h"
#include "rapidjson/stringbuffer.h"

#define JSON_CONFIG_FILTER_ELEM "filter"
#define JSON_CONFIG_PIPELINE_ELEM "pipeline"

using namespace std;

/**
 * FilterPipeline class constructor
 *
 * This class abstracts the filter pipeline interface
 *
 * @param mgtClient	Management client handle
 * @param storage	Storage client handle
 * @param serviceName	Name of the service to which this pipeline applies
 */
FilterPipeline::FilterPipeline(ManagementClient* mgtClient, StorageClient& storage, string serviceName) : 
			mgtClient(mgtClient), storage(storage), serviceName(serviceName), m_ready(false), m_shutdown(false)
{
}

/**
 * FilterPipeline destructor
 */
FilterPipeline::~FilterPipeline()
{
}

/**
 * Load the specified filter plugin
 *
 * @param filterName	The filter plugin to load
 * @return		Plugin handle on success, NULL otherwise 
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
 * Load all filter plugins in the pipeline
 *
 * @param categoryName	Configuration category name
 * @return		True if filters are loaded (or no filters at all)
 *			False otherwise
 */
bool FilterPipeline::loadFilters(const string& categoryName)
{
	vector<string> children;	// The Child categories of 'Filters'
	try
	{
		// Get the category with values and defaults
		ConfigCategory config = mgtClient->getCategory(categoryName);
		string filter = config.getValue(JSON_CONFIG_FILTER_ELEM);
		Logger::getLogger()->info("FilterPipeline::loadFilters(): categoryName=%s, filters=%s", categoryName.c_str(), filter.c_str());
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
					if (itr->IsString())
					{
						// Get "plugin" item from filterCategoryName
						string filterCategoryName = itr->GetString();
						ConfigCategory filterDetails = mgtClient->getCategory(filterCategoryName);

						PipelineFilter *element = new PipelineFilter(filterCategoryName, filterDetails);
						element->setServiceName(serviceName);
						m_filters.emplace_back(element);
					}
					else if (itr->IsArray())
					{
						// Sub pipeline
						Logger::getLogger()->warn("This version of Fledge does not support branching of pipelines. The branch will be ignored.");
					}
					else if (itr->IsObject())
					{
						// An object, probably the write destination
						Logger::getLogger()->warn("This version of Fledge does not support pipelines with different destinations. The destination will be ignored and the data written to the default storage service.");
					}
					else
					{
						Logger::getLogger()->error("Unexpected object in  pipeline definition %s, ignoring", categoryName.c_str());
					}
				}

				// We have kept filter default config in the filterInfo map
				// Handle configuration for each filter
				for (auto& itr : m_filters)
				{
					itr->setupConfiguration(mgtClient, children);
				}
			}
		}

		m_pipeline = filter;
		/*
		 * Put all the new catregories in the Filter category parent
		 * Create an empty South category if one doesn't exist
		 */
		string parentName = categoryName + " Filters";
		DefaultConfigCategory filterConfig(parentName, string("{}"));
		filterConfig.setDescription("Filters for " + categoryName);
		mgtClient->addCategory(filterConfig, true);
		mgtClient->addChildCategories(parentName, children);
		vector<string> children1;
		children1.push_back(parentName);
		mgtClient->addChildCategories(categoryName, children1);
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
 * This method calls the method "plugin_init" for all loadad filters.
 * Up-to-date filter configurations and Ingest filtering methods
 * are passed to "plugin_init"
 *
 * @param passToOnwardFilter	Ptr to function that passes data to next filter
 * @param useFilteredData	Ptr to function that gets final filtered data
 * @param ingest		The ingest class handle
 * @return 		True on success,
 *			False otherwise.
 * @thown		Any caught exception
 */
bool FilterPipeline::setupFiltersPipeline(void *passToOnwardFilter, void *useFilteredData, void *ingest)
{
	bool initErrors = false;
	string errMsg = "'plugin_init' failed for filter '";
	for (auto it = m_filters.begin(); it != m_filters.end(); ++it)
	{
		vector<string> children;
		
		try
		{
			if ((*it)->isFilter())
			{
				PipelineFilter *filter = (PipelineFilter *)*it;
				string filterCategoryName = filter->getCategoryName();
				Logger::getLogger()->info("Load plugin categoryName %s", filterCategoryName.c_str());
				// Fetch up to date filter configuration
				ConfigCategory updatedCfg = mgtClient->getCategory(filterCategoryName);

				// Pass Management client IP:Port to filter so that it may connect to bucket service
				updatedCfg.addItem("mgmt_client_url_base", "Management client host and port",
									"string", "127.0.0.1:0",
									mgtClient->getUrlbase());

				// Add filter category name under service/process config name
				children.push_back(filterCategoryName);
				mgtClient->addChildCategories(serviceName, children);
				
				ConfigHandler *configHandler = ConfigHandler::getInstance(mgtClient);
				configHandler->registerCategory((ServiceHandler *)ingest, filterCategoryName);
				m_serviceHandler = (ServiceHandler *)ingest;
				
				m_filterCategories[filterCategoryName] = *it;

				// Iterate the load filters set in the Ingest class m_filters member 
				if ((it + 1) != m_filters.end())
				{
					// Set next filter pointer as OUTPUT_HANDLE
					if (!(*it)->init(&updatedCfg,
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
					if (!(*it)->init(&updatedCfg,
							 (OUTPUT_HANDLE *)(ingest),
							 filterReadingSetFn(useFilteredData)))
					{
						errMsg += (*it)->getName() + "'";
						initErrors = true;
						break;
					}
				}

			}
			else
			{
				// Not a plugin
			}
		}
		// TODO catch specific exceptions
		catch (...)
		{		
			throw;		
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

/**
 * Cleanup all the loaded filters
 *
 * Call "plugin_shutdown" method and free the FilterPlugin object
 *
 * @param categoryName		Configuration category name
 *
 */
void FilterPipeline::cleanupFilters(const string& categoryName)
{
	// Cleanup filters, in reverse order
	for (auto it = m_filters.rbegin(); it != m_filters.rend(); ++it)
	{
		PipelineElement *element = *it;
		ConfigHandler *configHandler = ConfigHandler::getInstance(mgtClient);
		element->shutdown(m_serviceHandler, configHandler);

		// Free filter
		delete element;
	}
}

/**
 * Configuration change for one of the filters. Lookup the category name and
 * find the plugin to call. Call the reconfigure method of that plugin with
 * the new configuration.
 *
 * @param category	The name of the configuration category
 * @param newConfig	The new category contents
 */
void FilterPipeline::configChange(const string& category, const string& newConfig)
{
	auto it = m_filterCategories.find(category);
	if (it != m_filterCategories.end())
	{
		it->second->reconfigure(newConfig);
	}
}

