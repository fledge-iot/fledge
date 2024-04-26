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
#include <config_handler.h>

/**
 * The base pipeline element class
 */
class PipelineElement {
	public:
		PipelineElement() : m_next(NULL), m_storage(NULL) {};
		virtual ~PipelineElement() {};
		void			setNext(PipelineElement *next)
					{
						m_next = next;
					};
		PipelineElement		*getNext()
					{
						return m_next;
					};
		void			setService(const std::string& serviceName)
					{
						m_serviceName = serviceName;
					};
		void			setStorage(StorageClient *storage)
					{
						m_storage = storage;
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
		virtual bool		isBranch()
			       		{
						return false;
					};
		virtual void		ingest(READINGSET *readingSet) = 0;
		virtual bool		setup(ManagementClient *mgmt, void *ingest, std::map<std::string, PipelineElement*>& categories) = 0;
		virtual bool		init(OUTPUT_HANDLE* outHandle, OUTPUT_STREAM output) = 0;
		virtual void		shutdown(ServiceHandler *serviceHandler, ConfigHandler *configHandler) = 0;
		virtual void		reconfigure(const std::string& newConfig)
					{
					};
		virtual std::string	getName() = 0;
		virtual bool		isReady() = 0;
	protected:
		std::string		m_serviceName;
		PipelineElement		*m_next;
		StorageClient		*m_storage;

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
		bool			setup(ManagementClient *mgmt, void *ingest, std::map<std::string, PipelineElement*>& categories);
		bool			init(OUTPUT_HANDLE* outHandle, OUTPUT_STREAM output);
		void			shutdown(ServiceHandler *serviceHandler, ConfigHandler *configHandler);
		void			reconfigure(const std::string& newConfig);
		bool			isFilter() { return true; };
		std::string		getCategoryName() { return m_categoryName; };
		bool			persistData() { return m_plugin->persistData(); };
		void			setPluginData(PluginData *data) { m_plugin->m_plugin_data = data; };
		std::string		getPluginData() { return m_plugin->m_plugin_data->loadStoredData(m_serviceName + m_name); };
		void			setServiceName(const std::string& name) { m_serviceName = name; };
		std::string		getName() { return m_name; };
		bool			isReady() { return true; };
	private:
		PLUGIN_HANDLE		loadFilterPlugin(const std::string& filterName);
	private:
		std::string		m_name;		// The name of the filter instance
		std::string		m_categoryName;
		std::string		m_pluginName;
		PLUGIN_HANDLE		m_handle;
		FilterPlugin		*m_plugin;
		std::string		m_serviceName;
		ConfigCategory		m_updatedCfg;
};

/**
 * A pipeline element that represents a branch in the pipeline
 */
class PipelineBranch : public PipelineElement {
	public:
		PipelineBranch();
		void			ingest(READINGSET *readingSet);
		std::string		getName() { return "Branch"; };
		bool			setup(ManagementClient *mgmt, void *ingest, std::map<std::string, PipelineElement*>& categories);
		bool                    init(OUTPUT_HANDLE* outHandle, OUTPUT_STREAM output);
		void                    shutdown(ServiceHandler *serviceHandler, ConfigHandler *configHandler);
		bool                    isReady();
		bool			isBranch()
					{
						return true;
					};
		std::vector<PipelineElement *>&	
					getBranchElements()
					{
						return m_branch;
					};
		void			setFunctions(void *onward, void *use, void *ingest)
					{
						m_passOnward = onward;
						m_useData = use;
						m_ingest = ingest;
					};
	private:
		std::vector<PipelineElement *>		m_branch;
		std::thread				*m_thread;
		std::queue<READINGSET *>		m_queue;
		void					*m_passOnward;
		void					*m_useData;
		void					*m_ingest;
};

/**
 * A pipeline element that writes to a storage service or buffer
 */
class PipelineWriter : public PipelineElement {
	public:
		PipelineWriter();
		void			ingest(READINGSET *readingSet);
		bool			setup(ManagementClient *mgmt, void *ingest, std::map<std::string, PipelineElement*>& categories);
		bool                    init(OUTPUT_HANDLE* outHandle, OUTPUT_STREAM output);
		void                    shutdown(ServiceHandler *serviceHandler, ConfigHandler *configHandler);
		bool                    isReady();
};

#endif
