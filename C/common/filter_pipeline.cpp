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

				loadPipeline(filterList, m_filters);

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

void FilterPipeline::loadPipeline(const Value& filterList, vector<PipelineElement *>& pipeline)
{
	// Try loading all filter plugins: abort on any error
	for (Value::ConstValueIterator itr = filterList.Begin(); itr != filterList.End(); ++itr)
	{
		if (itr->IsString())
		{
			// Get "plugin" item from filterCategoryName
			string filterCategoryName = itr->GetString();
			Logger::getLogger()->info("Creating pipeline filter %s", filterCategoryName.c_str());
			try {
				ConfigCategory filterDetails = mgtClient->getCategory(filterCategoryName);

				PipelineFilter *element = new PipelineFilter(filterCategoryName, filterDetails);
				element->setServiceName(serviceName);
				element->setStorage(&storage);
				pipeline.emplace_back(element);
			} catch (exception& e) {
				Logger::getLogger()->error("Failed to create filter %s: %s",
						filterCategoryName.c_str(), e.what());
			} catch (exception *e) {
				Logger::getLogger()->error("Failed to create filter %s: %s",
						filterCategoryName.c_str(), e->what());
			}
		}
		else if (itr->IsArray())
		{
			// Sub pipeline
			Logger::getLogger()->info("Creating pipeline branch");
			PipelineBranch *element = new PipelineBranch(this);
			loadPipeline(*itr, element->getBranchElements());
			pipeline.emplace_back(element);
		}
		else if (itr->IsObject())
		{
			// An object, probably the write destination
			Logger::getLogger()->warn("This version of Fledge does not support pipelines with different destinations. The destination will be ignored and the data written to the default storage service.");
		}
		else
		{
			Logger::getLogger()->error("Unexpected object in pipeline definition, ignoring");
		}
	}

	// End the pipeline with a writer element that sends data to the
	// ingest of the storage system
	PipelineWriter *element = new PipelineWriter();
	pipeline.emplace_back(element);
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
		
		try
		{
			if ((*it)->isBranch())
			{
				Logger::getLogger()->info("Set branch functions");
				PipelineBranch *branch = (PipelineBranch *)(*it);
				branch->setFunctions(passToOnwardFilter, useFilteredData, ingest);
			}
			Logger::getLogger()->info("Setup element %s", (*it)->getName().c_str());
			(*it)->setup(mgtClient, ingest, m_filterCategories);
			// Iterate the load filters set in the Ingest class m_filters member 
			if ((it + 1) != m_filters.end())
			{
				(*it)->setNext(*(it + 1));
				// Set next filter pointer as OUTPUT_HANDLE
				try {
					if (!(*it)->init((OUTPUT_HANDLE *)(*(it + 1)),
							filterReadingSetFn(passToOnwardFilter)))
					{
						errMsg += (*it)->getName() + "'";
						initErrors = true;
						break;
					}
				} catch (exception& e) {
					Logger::getLogger()->error("Unable to initialise plugin %s, %s", (*it)->getName().c_str(), e.what());
					initErrors = true;
					break;
				}
			}
			else
			{
				// Set the Ingest class pointer as OUTPUT_HANDLE
				try {
					if (!(*it)->init((OUTPUT_HANDLE *)(ingest),
							 filterReadingSetFn(useFilteredData)))
					{
						errMsg += (*it)->getName() + "'";
						initErrors = true;
						break;
					}
				} catch (exception& e) {
					Logger::getLogger()->error("Unable to initialise plugin %s, %s", (*it)->getName().c_str(), e.what());
					initErrors = true;
					break;
				}
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
		Logger::getLogger()->fatal("Failed to create pipeline,  %s", errMsg.c_str());
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

	// Shutdown filters - do this down the pipeline, starting
	// from the first filter in the pipeline. This allows a filter
	// to asynchronously send data in the shutdown call to the
	// next element in the pipeline since that next element has
	// not yet been asked to shutdown.
	//
	// This is not behaviour that is encouraged or designed, but a
	// small number of Python filters have implemented sending data
	// during shutdown, hence the need to ensure that data has
	// somewhere to go.
	for (auto it = m_filters.begin(); it != m_filters.end(); ++it)
	{
		PipelineElement *element = *it;
		ConfigHandler *configHandler = ConfigHandler::getInstance(mgtClient);
		element->shutdown(m_serviceHandler, configHandler);
	}
	// Delete filters, in reverse order
	for (auto it = m_filters.rbegin(); it != m_filters.rend(); ++it)
	{
		PipelineElement *element = *it;
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

/**
 * Called when we pass the data into the pipeline. Set the
 * number of active branches to 1
 */
void FilterPipeline::execute()
{
	unique_lock<mutex> lck(m_actives);
	m_activeBranches = 1;
}

/**
 * Wait for all active branches of the pipeline to complete
 */
void FilterPipeline::awaitCompletion()
{
	unique_lock<mutex> lck(m_actives);
	while (m_activeBranches > 0)
	{
		m_branchActivations.wait(lck);
	}
}

/**
 * A new branch has started in the pipeline
 */
void FilterPipeline::startBranch()
{
	unique_lock<mutex> lck(m_actives);
	m_activeBranches++;
}

/**
 * A branch in the pipeline has completed
 */
void FilterPipeline::completeBranch()
{
	unique_lock<mutex> lck(m_actives);
	m_activeBranches--;
	if (m_activeBranches == 0)
	{
		m_branchActivations.notify_all();
	}
}

/**
 * Attach the debugger to the pipeline elements
 *
 * @return bool	True if the pipeline was attached
 */
bool FilterPipeline::attachDebugger()
{
	bool rval =  attachDebugger(m_filters);
	setDebuggerBuffer(1);
	return rval;
}

/**
 * Attach the debugger to the pipeline elements
 *
 * @param pipeline	The pipeline (or branch) to attach the debugger
 * @return bool		True if the debugger was attached
 */
bool FilterPipeline::attachDebugger(const vector<PipelineElement *>& pipeline)
{
	bool ret = true;
	for (auto& elem : pipeline)
	{
		if (!elem->attachDebugger())
		{
			ret = false;
			break;
		}
		if (elem->isBranch())
		{
			PipelineBranch *branch = (PipelineBranch *)elem;
			if (!attachDebugger(branch->getBranchElements()))
			{
				ret = false;
				break;
			}
		}
	}
	if (!ret)
	{
		// Detach any partially attached pipeline
		detachDebugger(pipeline);
	}
	return ret;
}

/**
 * Detach the debugger from the pipeline elements
 */
void FilterPipeline::detachDebugger()
{
	detachDebugger(m_filters);
}

/**
 * Detach the debugger from the pipeline elements
 *
 * @param pipeline	The pipeline or branch to detach the debugger from
 */
void FilterPipeline::detachDebugger(const vector<PipelineElement *>& pipeline)
{
	for (auto& elem : pipeline)
	{
		elem->detachDebugger();
		if (elem->isBranch())
		{
			PipelineBranch *branch = (PipelineBranch *)elem;
			detachDebugger(branch->getBranchElements());
		}
	}
}

/**
 * Set the debugger buffer size to the pipeline elements
 *
 * @param size	The request number of readings to buffer
 */
void FilterPipeline::setDebuggerBuffer(unsigned int size)
{
	setDebuggerBuffer(m_filters, size);
}

/**
 * Set the debugger buffer size to the pipeline elements
 *
 * @param pipeline	The pipeline or branch to set the buffer size for
 * @param size		The desired number of readings to buffer
 */
void FilterPipeline::setDebuggerBuffer(const vector<PipelineElement *>& pipeline, unsigned int size)
{
	for (auto& elem : pipeline)
	{
		elem->setDebuggerBuffer(size);
		if (elem->isBranch())
		{
			PipelineBranch *branch = (PipelineBranch *)elem;
			setDebuggerBuffer(branch->getBranchElements(), size);
		}
	}
}

/**
 * Get the debugger buffer contents for all the pipeline elements
 *
 * @return string	JSON document with all the buffer contents
 */
string FilterPipeline::getDebuggerBuffer()
{
	string	rval = "{ \"data\" : [";
	rval += getDebuggerBuffer(m_filters);
	rval += "]}";
	return rval;
}



/**
 * Get the debugger buffer contents for all the pipeline elements
 *
 * @param pipeline	The pipeline to fetch the buffered data from
 * @return string	JSON document with all the buffer contents
 */
string FilterPipeline::getDebuggerBuffer(const vector<PipelineElement *>& pipeline)
{
	string rval;

	for (auto& elem : pipeline)
	{
		vector<shared_ptr<Reading>> buf = elem->getDebuggerBuffer();
		rval += "{ \"name\" : \"";
		rval += elem->getName();
		rval += "\", \"readings\" : [ ";
		rval += readingsToJSON(buf);
		rval += "] }";
		if (elem->getNext())
			rval += ",";
		if (elem->isBranch())
		{
			PipelineBranch *branch = (PipelineBranch *)elem;
			rval += "[ ";
			rval += getDebuggerBuffer(branch->getBranchElements());
			rval += "], ";
		}
	}

	return rval;
}

/**
 * Get the debugger buffer contents for all the pipeline elements
 *
 * @param name		The name of the filter element we return the buffer from
 * @return string	JSON document with all the buffer contents
 */
string FilterPipeline::getDebuggerBuffer(const string& name)
{
	string	rval;

	for (auto& elem : m_filters)
	{
		if (elem->getName().compare(name) == 0)
		{
			vector<shared_ptr<Reading>> buf = elem->getDebuggerBuffer();
			rval += "{ \"name\" : \"";
			rval += name;
			rval += "\", ";
			rval += readingsToJSON(buf);
			rval += "}";
		}
	}
	return rval;
}

/**
 * Convert a vector of readings into JSON that we can use to return 
 * the buffered data held at each stage within the filter pipeline.
 *
 * @param readings	A vector of shared pointers to readings
 * @return string	A JSON structure containing the pipeline buffers
 */
string FilterPipeline::readingsToJSON(vector<shared_ptr<Reading>> readings)
{
	string rval;

	for (int j = 0; j < readings.size(); j++)
	{
		shared_ptr<Reading> reading = readings[j];
		rval += reading->toJSON();
		if (j < readings.size() - 1)
				rval += ",";
	}

	return rval;
}

/**
 * Replay the data in the first saved buffer to the filter pipeline
 */
void FilterPipeline::replayDebugger()
{
ReadingSet 		*replay;
vector<Reading *>	*readings = new vector<Reading *>;
PipelineElement		*first = m_filters[0]; 

	vector<shared_ptr<Reading>> buf = first->getDebuggerBuffer();
	for (int i = 0; i < buf.size(); i++)
	{
		readings->emplace_back(new Reading(*buf[i].get()));
	}
	replay = new ReadingSet(readings);

	first->ingest(replay);
}
