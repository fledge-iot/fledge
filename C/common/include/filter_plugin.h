#ifndef _FILTER_PLUGIN_H
#define _FILTER_PLUGIN_H
/*
 * FogLAMP filter plugin class.
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Massimiliano Pinto
 */
#include <plugin.h>
#include <plugin_manager.h>
#include <config_category.h>
#include <management_client.h>
#include <plugin_data.h>

// This is a C++ ReadingSet class instance passed through
typedef void READINGSET;
// Data handle passed to function pointer
typedef void OUTPUT_HANDLE;
// Function pointer called by "plugin_ingest" plugin method
typedef void (*OUTPUT_STREAM)(OUTPUT_HANDLE *, READINGSET *);

// FilterPlugin class
class FilterPlugin : public Plugin
{

public:
        FilterPlugin(const std::string& name,
		     PLUGIN_HANDLE handle);
        ~FilterPlugin();

	const std::string	getName() const { return m_name; };
        PLUGIN_HANDLE		init(const ConfigCategory& config,
				     OUTPUT_HANDLE* outHandle,
				     OUTPUT_STREAM outputFunc);
        void			shutdown();
        void			ingest(READINGSET *);
	bool			persistData() { return info->options & SP_PERSIST_DATA; };
	void			startData(const std::string& pluginData);
	std::string		shutdownSaveData();
	void			start();

// Public static methods
public:
	static PLUGIN_HANDLE	loadFilterPlugin(const std::string& filterName);
	// Cleanup the loaded filters
	static void 		cleanupFilters(std::vector<FilterPlugin *>& loadedFilters,
					       const std::string& categoryName);
	// Load filters as specified in the configuration
	static bool		loadFilters(const std::string& categoryName,
					    std::vector<FilterPlugin *>& filters,
					    ManagementClient* manager);

private:
	PLUGIN_HANDLE	(*pluginInit)(const ConfigCategory* config,
				      OUTPUT_HANDLE* outHandle,
				      OUTPUT_STREAM output);
        void            (*pluginShutdownPtr)(PLUGIN_HANDLE);
        void            (*pluginIngestPtr)(PLUGIN_HANDLE,
					   READINGSET *);
	std::string	(*pluginShutdownDataPtr)(const PLUGIN_HANDLE);
	void		(*pluginStartDataPtr)(PLUGIN_HANDLE,
					      const std::string& pluginData);
	void		(*pluginStartPtr)(PLUGIN_HANDLE);

public:
	// Persist plugin data
	PluginData*	m_plugin_data;

private:
	std::string	m_name;
        PLUGIN_HANDLE   m_instance;
};

#endif
