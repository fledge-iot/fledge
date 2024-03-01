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

/**
 * The base pipeline element class
 */
class PipelineElement {
	public:
		PipelineElement();
		void			setNext(PipelineElement *next)
					{
						m_next = next;
					};
		void			setService(const std::string& serviceName)
					{
						m_serviceName = serviceName;
					};
	protected:
		bool			setupConfiguration(ManagementClient *mgtClient, PluginManager *manager, vector<std::string& children>& children) {};
		void			ingest(READINGSET *readingSet) = 0;
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
	protected:
		bool			setupConfiguration(ManagementClient *mgtClient, PluginManager *manager, vector<std::string& children>& children);
		void			ingest(READINGSET *readingSet)
					{
						if (m_plugin)
						{
							m_plugin->ingest(readingSet);
						}
					};
	private:
		std::string		m_name;		// The name of the filter category
		std::string		m_pluginName;
		PLUGIN_HANDLE		*m_handle;
		FilterPlugin		*m_plugin;
};

/**
 * A pipeline element that represents a branch in the pipeline
 */
class PipelineBranch : public PipelineElement {
	public:
		PipelineBranch();
	protected:
		void			ingest(READINGSET *readingSet);
};

/**
 * A pipeline element that writes to a storage service or buffer
 */
class PipelineWriter : public PipelineElement {
	public:
		PipelineWriter();
	protected:
		void			ingest(READINGSET *readingSet);
};

#endif
