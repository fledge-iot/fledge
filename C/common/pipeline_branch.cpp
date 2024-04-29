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
	m_shutdownCalled = false;
}

/**
 * Setup the configuration for a branch in a pipeline
 *
 * @param       mgtClient       The managament client
 * @param       children        A vector to fill with child configuration categories
 */
bool PipelineBranch::setupConfiguration(ManagementClient *mgtClient, vector<string>& children)
{
	for (auto it = m_branch.begin(); it != m_branch.end(); ++it)
	{
		(*it)->setupConfiguration(mgtClient, children);
	}
	return true;
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

	Logger::getLogger()->info("Calling setup for pipeline branch");
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
 * Initialise the elements of the child pipeline
 * Spawn a thread to excute the child pipeline.
 *
 * @param config	The filter configuration
 * @param outHandle	The pipeline element on the "main branch"
 * @param output
 */
bool PipelineBranch::init(OUTPUT_HANDLE* outHandle, OUTPUT_STREAM output)
{
	bool initErrors = false;
	string errMsg = "'plugin_init' failed for filter '";
	Logger::getLogger()->info("Calling init for pipeline branch");
	for (auto it = m_branch.begin(); it != m_branch.end(); ++it)
	{
		try
		{
			Logger::getLogger()->info("Initialise %s on pipeline branch", (*it)->getName().c_str());
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

	Logger::getLogger()->info("Create branch handler thread");
	m_thread = new thread(PipelineBranch::branchHandler, this);

	//Success
	return true;
}

/**
 * Ingest a set of readings and pass on in the pipeline. Create a deep copy
 * and queue the copy into the branched pipeline.
 *
 * @param readingSet	The set of readings to ingest
 */
void PipelineBranch::ingest(READINGSET *readingSet)
{
	READINGSET *copy = new ReadingSet();
	copy->copy(*readingSet);
	unique_lock<mutex> lck(m_mutex);
	m_queue.push(copy);
	lck.unlock();
	m_cv.notify_one();
	if (m_next)
	{
		Logger::getLogger()->info("Branch sending data onwards in main branch");
		m_next->ingest(readingSet);
	}
	else
	{
		Logger::getLogger()->warn("Pipeline branch has no downstream element");
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
	// Shutdown the handler thread
	m_shutdownCalled = true;
	m_cv.notify_all();
	m_thread->join();

	// Shutdown the fitler elements on the branch
	for (auto it = m_branch.begin(); it != m_branch.end(); ++it)
	{
		(*it)->shutdown(serviceHandler, configHandler);
	}

	// Clear any queued readings
	while (!m_queue.empty())
	{
		ReadingSet *readings = m_queue.front();
		m_queue.pop();
		delete readings;
	}
}

bool PipelineBranch::isReady()
{
	return true;
}

/**
 * Static entry point for the thread that handles sending data on the
 * branch
 *
 * @param instance	The instance of the PipelineBranch
 */
void PipelineBranch::branchHandler(void *instance)
{
	PipelineBranch *branch = (PipelineBranch *)instance;
	branch->handler();
}

/**
 * The handler for readings in an instance of a branch.
 * Loop waiting for data or a shutdown signal and pass the
 * queued data to the first filter in the pipeline branch
 */
void PipelineBranch::handler()
{
	Logger::getLogger()->info("Starting thread to process branch pipeline");
	while (!m_shutdownCalled)
	{
		unique_lock<mutex> lck(m_mutex);
		while (m_queue.empty())
		{
			m_cv.wait(lck);
			if (m_shutdownCalled)
			{
				return;
			}
		}
		ReadingSet *readings = m_queue.front();
		m_queue.pop();
		lck.unlock();
		Logger::getLogger()->info("Branch sending data onwards in child branch");
		m_branch[0]->ingest(readings);
	}
}
