#ifndef _FILTER_PIPELINE_H
#define _FILTER_PIPELINE_H
/*
 * FogLAMP filter plugin class.
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

// FilterPlugin class
class FilterPipeline
{

public:
        FilterPipeline();
        ~FilterPipeline();

		//const std::string	getName() const { return m_name; };
       /* PLUGIN_HANDLE		init(const ConfigCategory& config,
				     OUTPUT_HANDLE* outHandle,
				     OUTPUT_STREAM outputFunc);
        void			shutdown();
        void			ingest(READINGSET *); */
	//bool			persistData() { return info->options & SP_PERSIST_DATA; };
	//void			startData(const std::string& pluginData);
	//std::string		shutdownSaveData();
	//void			start();
	FilterPlugin *	getFirstFilterPlugin() { return (m_filters.begin() == m_filters.end()) ? NULL : *(m_filters.begin()); }
	unsigned int	getFilterCount() { return m_filters.size(); }
	void		configChange(const std::string&, const std::string&);

public:
	PLUGIN_HANDLE	loadFilterPlugin(const std::string& filterName);
	// Cleanup the loaded filters
	void 		cleanupFilters(const std::string& categoryName);
	// Load filters as specified in the configuration
	bool		loadFilters(const std::string& categoryName, ManagementClient* manager);
	bool		setupFiltersPipeline(ManagementClient*, StorageClient&, std::string,
				void *passToOnwardFilter, void *useFilteredData, void *ingest);

private:
	std::vector<FilterPlugin *> m_filters;
	std::map<std::string, FilterPlugin *>	m_filterCategories;
};

#endif
