#ifndef _FILTER_PIPELINE_H
#define _FILTER_PIPELINE_H
/*
 * Fledge filter pipeline class.
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Amandeep Singh Arora
 */
#include <plugin.h>
#include <plugin_manager.h>
#include <config_category.h>
#include <management_client.h>
#include <plugin_data.h>
#include <reading_set.h>
#include <filter_plugin.h>
#include <service_handler.h>
#include <pipeline_element.h>
typedef void (*filterReadingSetFn)(OUTPUT_HANDLE *outHandle, READINGSET* readings);

/**
 * The FilterPipeline class is used to represent a pipeline of filters 
 * applicable to a task/service. Methods are provided to load filters, 
 * setup filtering pipeline and for pipeline/filters cleanup.
 */
class FilterPipeline
{

public:
	FilterPipeline(ManagementClient* mgtClient,
			StorageClient& storage,
			std::string serviceName);
	~FilterPipeline();
	PipelineElement *getFirstFilterPlugin()
	{
		return (m_filters.begin() == m_filters.end()) ?
			NULL : *(m_filters.begin());
	};
	unsigned int	getFilterCount() { return m_filters.size(); }
	void		configChange(const std::string&, const std::string&);
	
	// Cleanup the loaded filters
	void 		cleanupFilters(const std::string& categoryName);
	// Load filters as specified in the configuration
	bool		loadFilters(const std::string& categoryName);
	// Setup the filter pipeline
	bool		setupFiltersPipeline(void *passToOnwardFilter,
					     void *useFilteredData,
					     void *ingest);
	// Check FilterPipeline is ready for data ingest
	bool		isReady() { return m_ready; };
	bool		hasChanged(const std::string pipeline) const { return m_pipeline != pipeline; }
	bool		isShuttingDown() { return m_shutdown; };
	void 		setShuttingDown() { m_shutdown = true; }
	void		execute();
	void		awaitCompletion();
	void		startBranch();
	void		completeBranch();

private:
	PLUGIN_HANDLE	loadFilterPlugin(const std::string& filterName);
	void		loadPipeline(const rapidjson::Value& filters, std::vector<PipelineElement *>& pipeline);

protected:
	ManagementClient*	mgtClient;
	StorageClient&		storage;
	std::string		serviceName;
	std::vector<PipelineElement *>
				m_filters;
	std::map<std::string, PipelineElement *>
				m_filterCategories;
	std::string		m_pipeline;
	bool			m_ready;
	bool			m_shutdown;
	ServiceHandler		*m_serviceHandler;
	int			m_activeBranches;
	std::mutex		m_actives;
	std::condition_variable	m_branchActivations;
};

#endif
