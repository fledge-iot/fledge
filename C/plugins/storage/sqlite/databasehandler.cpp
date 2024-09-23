/*
 * Fledge SQLite storage plugin database handler thread
 *
 * Copyright (c) 2024 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */

#include <logger.h>
#include <stdexcept>
#include <databasehandler.h>

using namespace std;

/**
 * Thread entry point
 */
void DatabaseHandler::handlerEntry(void *arg)
{
	DatabaseHandler *handler = (DatabaseHandler *)arg;
	handler->handler();
}


/**
 * Constructor for the database handler
 */
DatabaseHandler::DatabaseHandler() : m_shutdown(false)
{
	m_logger = Logger::getLogger();
	m_thread = new thread(handlerEntry, this);
}

/**
 * Destructor for the database thread handler
 */
DatabaseHandler::~DatabaseHandler()
{
	m_shutdown = true;
	m_cv.notify_all();
	m_thread->join();
	delete m_thread;
}

/**
 * The queue handler thread for the database handler
 */
void DatabaseHandler::handler()
{
	unique_lock<mutex> lck(m_mutex);
	while (!m_shutdown)
	{
		while (!m_queue.empty())
		{
			DBCB *cb = m_queue.front();
			m_queue.pop();
			lck.unlock();
			cb->execute();
			lck.lock();
		}
		m_cv.wait(lck);
	}
}

/**
 * Queue the database request block to the handler thread for
 * this database
 *
 * @param request	The request to be queued
 * @return bool		True if the request was queued
 */
bool DatabaseHandler::queueRequest(DBCB *request)
{
	unique_lock<mutex> lck(m_mutex);
	if (m_shutdown)
	{
		// Once shutdown has started we do not accept new requests
		return false;
	}
	m_queue.push(request);
	m_cv.notify_all();
	return true;
}
