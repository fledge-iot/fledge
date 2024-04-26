/*
 * Fledge pipeline branch class
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
 * Constructor for a branch in a filter pipeline
 */
PipelineBranch::PipelineBranch() : PipelineElement()
{
}

/**
 * Setup the configuration categories for the branch element of
 * a pipeline. The branch itself has no category, but it must call
 * the setup method on all items in the child branch of the
 * piepline.
 *
 * @param	mgmt		The management client
 * @param	ingest		The configuration handler for our service
 * @param	filterCategories	A map of the category names to pipeline elements
 */
bool PipelineBranch::setup(ManagementClient *mgmt, void *ingest, map<string, PipelineElement *>&  filterCategories)
{
vector<string> children;

	for (auto it = m_branch.begin(); it != m_branch.end(); ++it)
	{
		if ((*it)->isBranch())
		{
			PipelineBranch *branch = (PipelineBranch *)(*it);
			branch->setFunctions(m_passOnward, m_useData, m_ingest);
		}
		(*it)->setup(mgmt, ingest, filterCategories);
	}
	return true;
}
/**
 * Initialise the pipeline branch.
 *
 * Spawn a thread to excute the child pipeline.
 * Initialise the elements of the child pipeline
 *
 * @param config	The filter configuration
 * @param outHandle	The pipeline element on the "main branch"
 * @param output
 */
bool PipelineBranch::init(OUTPUT_HANDLE* outHandle, OUTPUT_STREAM output)
{
	bool initErrors = false;
	string errMsg = "'plugin_init' failed for filter '";
	for (auto it = m_branch.begin(); it != m_branch.end(); ++it)
	{
		try
		{
			// Iterate the load filters set in the Ingest class m_filters member 
			if ((it + 1) != m_branch.end())
			{
				// Set next filter pointer as OUTPUT_HANDLE
				if (!(*it)->init((OUTPUT_HANDLE *)(*(it + 1)),
						filterReadingSetFn(m_passOnward)))
				{
					errMsg += (*it)->getName() + "'";
					initErrors = true;
					break;
				}
			}
			else
			{
				// Set the Ingest class pointer as OUTPUT_HANDLE
				if (!(*it)->init((OUTPUT_HANDLE *)(m_ingest),
						 filterReadingSetFn(m_useData)))
				{
					errMsg += (*it)->getName() + "'";
					initErrors = true;
					break;
				}
			}

		}
		// TODO catch specific exceptions
		catch (...)
		{		
			throw;		
		}
	}

	if (initErrors)
	{
		// Failure
		Logger::getLogger()->fatal("%s error: %s", __FUNCTION__, errMsg.c_str());
		return false;
	}

	//Success
	return true;
}

/**
 * Ingest a set of reading and pass on in the pipeline and queue into the
 * branched pipeline.
 *
 * @param readingSet	The set of readings to ingest
 */
void PipelineBranch::ingest(READINGSET *readingSet)
{
	READINGSET *copy = new ReadingSet();
	copy->copy(*readingSet);
	m_queue.push(copy);
	if (m_next)
	{
		m_next->ingest(readingSet);
	}
}

/**
 * Setup the configuration categories for the branch element of
 * a pipeline. The branch itself has no category, but it must call
 * the setup method on all items in the child branch of the
 * piepline.
 *
 * @param	mgmt		The management client
 * @param	ingest		The configuration handler for our service
 * @param	filterCategories	A map of the category names to pipeline elements
 */
void PipelineBranch::shutdown(ServiceHandler *serviceHandler, ConfigHandler *configHandler)
{
}

bool PipelineBranch::isReady()
{
	return true;
}

