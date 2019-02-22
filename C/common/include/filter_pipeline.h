#ifndef _FILTER_PIPELINE_H
#define _FILTER_PIPELINE_H
/*
 * FogLAMP filter pipeline class.
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

typedef void (*filterReadingSetFn)(OUTPUT_HANDLE *outHandle, READINGSET* readings);

/**
 * The FilterPipeline class is used to represent a pipeline of filters 
 * applicable to a task/service. Methods are provided to load filters, 
 * setup filtering pipeline and for pipeline/filters cleanup.
 */
class FilterPipeline
{

public:
	FilterPipeline(ManagementClient* mgtClient, StorageClient& storage, std::string serviceName);
	~FilterPipeline();
	FilterPlugin *	getFirstFilterPlugin() { return (m_filters.begin() == m_filters.end()) ? NULL : *(m_filters.begin()); }
	unsigned int	getFilterCount() { return m_filters.size(); }
	void		configChange(const std::string&, const std::string&);
	
	// Cleanup the loaded filters
	void 		cleanupFilters(const std::string& categoryName);
	// Load filters as specified in the configuration
	bool		loadFilters(const std::string& categoryName);
	// Setup the filter pipeline
	bool		setupFiltersPipeline(void *passToOnwardFilter, void *useFilteredData, void *ingest);

private:
	PLUGIN_HANDLE	loadFilterPlugin(const std::string& filterName);

protected:
	ManagementClient*	mgtClient;
	StorageClient&		storage;
	std::string		serviceName;
	std::vector<FilterPlugin *>	m_filters;
	std::map<std::string, FilterPlugin *>	m_filterCategories;
};

#endif
