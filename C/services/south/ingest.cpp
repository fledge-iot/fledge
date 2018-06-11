/*
 * FogLAMP readings ingest.
 *
 * Copyright (c) 2018 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
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
Ingest::Ingest(StorageClient& storage, unsigned long timeout, unsigned int threshold) :
			m_storage(storage), m_timeout(timeout), m_queueSizeThreshold(threshold)
{
	m_running = true;
	m_queue = new vector<Reading *>();
	m_thread = new thread(ingestThread, this);
	m_logger = Logger::getLogger();
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
vector<Reading *> *savedQ, *newQ;
bool requeue = false;

	newQ = new vector<Reading *>();
	// Block of code to execute holding the mutex
	{
		lock_guard<mutex> guard(m_qMutex);
		savedQ = m_queue;
		m_queue = newQ;
	}
	if ((!savedQ->empty()) &&
			m_storage.readingAppend(*savedQ) == false && requeue == true)
	{
		m_logger->error("Failed to write readings to storage layer, buffering");
		lock_guard<mutex> guard(m_qMutex);
		m_queue->insert(m_queue->cbegin(), savedQ->begin(), savedQ->end());
	}
	else
	{
		for (vector<Reading *>::iterator it = savedQ->begin();
						 it != savedQ->end(); ++it)
		{
			Reading *reading = *it;
			delete(reading);
		}
	}
	delete savedQ;
}
