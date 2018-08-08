/*
 * FogLAMP readings ingest.
 *
 * Copyright (c) 2018 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch, Massimiliano Pinto
 */
#include <ingest.h>
#include <reading.h>
#include <chrono>
#include <thread>
#include <logger.h>

using namespace std;

/**
 * Thread to process the ingest queue and send the data
 * to the storage layer.
 */
static void ingestThread(Ingest *ingest)
{
	while (ingest->running())
	{
		ingest->waitForQueue();
		ingest->processQueue();
	}
}

/**
 * Construct an Ingest class to handle the readings queue.
 * A seperate thread is used to send the readings to the
 * storage layer based on time. This thread in created in
 * the constructor and will terminate when the destructor
 * is called.
 *
 * @param storage	The storage client to use
 * @param timeout	Maximum time before sending a queue of readings in milliseconds
 * @param threshold	Length of queue before sending readings
 */
Ingest::Ingest(StorageClient& storage,
		unsigned long timeout,
		unsigned int threshold) :
			m_storage(storage),
			m_timeout(timeout),
			m_queueSizeThreshold(threshold)
{
	m_running = true;
	m_queue = new vector<Reading *>();
	m_thread = new thread(ingestThread, this);
	m_logger = Logger::getLogger();
	m_data = NULL;
}

/**
 * Destructor for the Ingest class
 *
 * Set's the running flag to false. This will
 * cause the processing thread to drain the queue
 * and then exit.
 * Once this thread has exited the destructor will
 * return.
 */
Ingest::~Ingest()
{
	m_running = false;
	m_thread->join();
	processQueue();
	delete m_queue;
	delete m_thread;
	delete m_data;

	// Cleanup filters
	FilterPlugin::cleanupFilters(m_filters);
}

/**
 * Check if the ingest process is still running.
 * This becomes false when the service is shutdown
 * and is used to allow the queue to drain and then
 * the procssing routine to terminate.
 */
bool Ingest::running()
{
	return m_running;
}

/**
 * Add a reading to the reading queue
 */
void Ingest::ingest(const Reading& reading)
{
	lock_guard<mutex> guard(m_qMutex);
	m_queue->push_back(new Reading(reading));
	if (m_queue->size() >= m_queueSizeThreshold)
		m_cv.notify_all();
	
}

void Ingest::waitForQueue()
{
	mutex mtx;
	unique_lock<mutex> lck(mtx);
	m_cv.wait_for(lck,chrono::milliseconds(m_timeout));
}

/**
 * Process the queue of readings.
 *
 * Send them to the storage layer as a block. If the append call
 * fails requeue the readings for the next transmission.
 *
 * In order not to lock the queue for an excessie time a new queue
 * is created and the old one moved to a local variable. This minimise
 * the time we hold the queue mutex to the time it takes to swap two
 * variables.
 */
void Ingest::processQueue()
{
bool requeue = false;

	// Block of code to execute holding the mutex
	{
		lock_guard<mutex> guard(m_qMutex);
		m_data = m_queue;
	}

	ReadingSet* readingSet = NULL;

	// NOTE:
	// this first implementation with filters
	// create a ReadingSet from m_data readings if we have filters.
	// This means data being copied.
	//
	// This will be changed with next commits.
	if (m_filters.size())
	{
		auto it = m_filters.begin();
		readingSet = new ReadingSet(m_data);
		// Pass readingSet to filter chain
		(*it)->ingest(readingSet);		
	}

	/**
	 * 'm_data' vector is ready to be sent to storage service.
	 *
	 * Note: m_data might contain:
	 * - Readings set by the configured service "plugin" 
	 * OR
	 * - filtered readings by filter plugins in 'readingSet' object:
	 *	1- values only
	 *	2- some readings removed
	 *	3- New set of readings
	 */
	if ((!m_data->empty()) &&
			m_storage.readingAppend(*m_data) == false && requeue == true)
	{
		m_logger->error("Failed to write readings to storage layer, buffering");
		lock_guard<mutex> guard(m_qMutex);
		m_queue->insert(m_queue->cbegin(),
				m_data->begin(),
				m_data->end());
	}
	else
	{
		// Data sent to sorage service
		if (!readingSet)
		{
			// Data not filtered: remove the Readings in the vector
			for (vector<Reading *>::iterator it = m_data->begin();
							 it != m_data->end(); ++it)
			{
				Reading *reading = *it;
				delete reading;
			}
		}
		else
		{
			// Filtered data
			// Remove reading set (it contains copy of m_data)
			delete readingSet;
		}

		// We can remove current queued data
		delete m_queue;
		// Prepare the queue
		m_queue = new vector<Reading *>();
	}
}

/**
 * Pass the current readings set to the next filter in the pipeline
 *
 * Note:
 * This routine must be passed to all filters "plugin_init" except the last one
 *
 * Static method
 *
 * @param outHandle     Pointer to next filter
 * @param readings      Current readings set
 */
void Ingest::passToOnwardFilter(OUTPUT_HANDLE *outHandle,
				READINGSET *readingSet)
{
	// Get next filter in the pipeline
	FilterPlugin *next = (FilterPlugin *)outHandle;
	// Pass readings to next filter
	next->ingest(readingSet);
}

/**
 * Use the current input readings (they have been filtered
 * by all filters)
 *
 * Note:
 * This routine must be passed to last filter "plugin_init" only
 *
 * Static method
 *
 * @param outHandle     Pointer to Ingest class instance
 * @param readingSet    Filtered reading set being added to Ingest::m_data
 */
void Ingest::useFilteredData(OUTPUT_HANDLE *outHandle,
			     READINGSET *readingSet)
{
	Ingest* ingest = (Ingest *)outHandle;
	ingest->m_data = ((ReadingSet *)readingSet)->getAllReadingsPtr();
}
