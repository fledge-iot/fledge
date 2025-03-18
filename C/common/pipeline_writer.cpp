/*
 * Fledge pipeline writer class
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
 * Constructor for the pipeline writer, the element that sits
 * at the end of every pipeline and branch
 */
PipelineWriter::PipelineWriter()
{
}

/**
 * Ingest into a pipeline writer
 */
void PipelineWriter::ingest(READINGSET *readingSet)
{
	if (m_debugger)
	{
		PipelineDebugger::DebuggerActions action = m_debugger->process(readingSet);

		switch (action)
		{
		case PipelineDebugger::Block:
			delete readingSet;
			return;
		case PipelineDebugger::NoAction:
			break;
		}

	}
	(*m_useData)(m_ingest, readingSet);
}

/**
 * Setup the pipeline writer
 */
bool PipelineWriter::setup(ManagementClient *mgmt, void *ingest, std::map<std::string, PipelineElement*>& categories)
{
	return true;
}

/**
 * Initialise the pipeline writer
 */
bool PipelineWriter::init(OUTPUT_HANDLE* outHandle, OUTPUT_STREAM output)
{
	m_useData = output;
	m_ingest = outHandle;
	return true;
}

/**
 * Shutdown the pipeline writer
 */
void PipelineWriter::shutdown(ServiceHandler *serviceHandler, ConfigHandler *configHandler)
{
}

/**
 * Return if the pipeline writer is ready to receive data
 */
bool PipelineWriter::isReady()
{
	return true;
}
