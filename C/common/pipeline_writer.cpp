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
 * Ingest into a pipeline writer
 */
void PipelineWriter::ingest(READINGSET *readingSet)
{
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
