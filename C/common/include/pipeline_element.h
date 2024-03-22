#ifndef _PIPELINE_ELEMENT_H
#define _PIPELINE_ELEMENT_H
/*
 * Fledge filter pipeline elements.
 *
 * Copyright (c) 2024 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <string>
#include <config_category.h>
#include <management_client.h>
#include <plugin.h>
#include <plugin_manager.h>
#include <plugin_data.h>
#include <reading_set.h>
#include <filter_plugin.h>
#include <service_handler.h>

/**
 * The base pipeline element class
 */
class PipelineElement {
	public:
		PipelineElement() : m_next(NULL) {};
		virtual ~PipelineElement() {};
		void			setNext(PipelineElement *next)
					{
						m_next = next;
					};
		PipelineElement		*getNext(PipelineElement *next)
					{
						return m_next;
					};
		void			setService(const std::string& serviceName)
					{
						m_serviceName = serviceName;
					};
		static void		ingest(void *handle, READINGSET *readings)
					{
					       	((PipelineElement *)handle)->ingest(readings);
					};
		virtual bool		setupConfiguration(ManagementClient *mgtClient,
						std::vector<std::string>& children)
					{
						return false;
					};
		virtual bool		isFilter()
			       		{
						return false;
					};
		virtual void		ingest(READINGSET *readingSet) = 0;
		virtual bool		init(const ConfigCategory* config,
						OUTPUT_HANDLE* outHandle, OUTPUT_STREAM output) = 0;
	protected:
		std::string		m_serviceName;
		PipelineElement		*m_next;

};

/**
 * A pipeline element the runs a filter plugin
 */
class PipelineFilter : public PipelineElement {
	public:
		PipelineFilter(const std::string& name, const ConfigCategory& filterDetails);
		~PipelineFilter();
		bool			setupConfiguration(ManagementClient *mgtClient, std::vector<std::string>& children);
		void			ingest(READINGSET *readingSet)
					{
						if (m_plugin)
						{
							m_plugin->ingest(readingSet);
						}
					};
		bool			isFilter() { return true; };
		std::string		getCategoryName() { return m_categoryName; };
		bool			persistData() { return m_plugin->persistData(); };
		void			setPluginData(PluginData *data) { m_plugin->m_plugin_data = data; };
		std::string		getPluginData() { m_plugin->m_plugin_data->loadStoredData(serviceName + (*it)->getName()); };
	private:
		PLUGIN_HANDLE		loadFilterPlugin(const std::string& filterName);
	private:
		std::string		m_name;		// The name of the filter instance
		std::string		m_categoryName;
		std::string		m_pluginName;
		PLUGIN_HANDLE		m_handle;
		FilterPlugin		*m_plugin;
};

/**
 * A pipeline element that represents a branch in the pipeline
 */
class PipelineBranch : public PipelineElement {
	public:
		PipelineBranch();
		void			ingest(READINGSET *readingSet);
					{
						if (m_next)
						{
							m_next->ingest(readingSet);
						}
					};
	private:
		PipelineElement		*m_branch;
};

/**
 * A pipeline element that writes to a storage service or buffer
 */
class PipelineWriter : public PipelineElement {
	public:
		PipelineWriter();
		void			ingest(READINGSET *readingSet);
};

#endif
