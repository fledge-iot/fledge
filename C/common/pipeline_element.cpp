/*
 * Fledge pipeline element classes
 *
 * Copyright (c) 2024 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <pipeline_element.h>
#include <filter_pipeline.h>
#include <config_handler.h>
#include <service_handler.h>
#include "rapidjson/writer.h"
#include "rapidjson/stringbuffer.h"

using namespace std;

/**
 * Attach a debugger class to the pipeline
 *
 * @return bool		True if a debugger is attached to the element
 */
bool PipelineElement::attachDebugger()
{
	if (!m_debugger)
		m_debugger = new PipelineDebugger();
	return m_debugger ? true : false;
}

/**
 * Detach a pipeline debugger from the pipeline element
 */
void PipelineElement::detachDebugger()
{
	if (m_debugger)
		delete m_debugger;
	m_debugger = NULL;
}

/** 
 * Setup the size of the debug buffer
 *
 * @param size		Number of readings to buffer
 */
void PipelineElement::setDebuggerBuffer(unsigned int size)
{
	if (m_debugger)
	{
		if (size)
			m_debugger->setBuffer(size);
		else
			m_debugger->clearBuffer();
	}
}

/**
 * Fetch the content of the debugger buffer
 *
 * @return vector<shared_ptr<ReadingSet>>	The current contents of the debugger buffer
 */
vector<shared_ptr<Reading>> PipelineElement::getDebuggerBuffer()
{
	if (m_debugger)
	{
		return m_debugger->fetchBuffer();
	}
	vector<shared_ptr<Reading>> empty;

	return empty;
}
