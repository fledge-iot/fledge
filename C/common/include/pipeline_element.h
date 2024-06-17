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
					}
	private:
		PipelineElement		*m_next;

};

/**
 * A pipeline element the runs a filter plugin
 */
class PipelineFilter : public PipelineElement {
	public:
		PipelineFilter(const std::string& name);
	private:
		FilterPlugin		*m_plugin;
};

/**
 * A pipeline element that represents a branch in the pipeline
 */
class PipelineBranch : public PipelineElement {
	public:
		PipelineBranch();
};

/**
 * A pipeline element that writes to a storage service or buffer
 */
class PipelineWriter : public PipelineElement {
	public:
		PipelineWriter();
};

#endif
