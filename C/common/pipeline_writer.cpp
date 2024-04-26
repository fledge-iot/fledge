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

void PipelineWriter::ingest(READINGSET *readingSet)
{
}

bool PipelineWriter::setup(ManagementClient *mgmt, void *ingest, std::map<std::string, PipelineElement*>& categories)
{
	return true;
}

bool PipelineWriter::init(OUTPUT_HANDLE* outHandle, OUTPUT_STREAM output)
{
	return true;
}

void PipelineWriter::shutdown(ServiceHandler *serviceHandler, ConfigHandler *configHandler)
{
}

bool PipelineWriter::isReady()
{
	return true;
}
