/*
 * Fledge North Service Data Loading.
 *
 * Copyright (c) 2020 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <data_sender.h>
#include <data_load.h>
#include <north_service.h>
#include <reading.h>

using namespace std;

/**
 * Start the sending thread within the DataSender class
 *
 * @param data	The instance of the class DataSender
 */
static void startSenderThread(void *data)
{
	DataSender *sender = (DataSender *)data;
	sender->sendThread();
}

/**
 * Constructor for the data sending class
 */
DataSender::DataSender(NorthPlugin *plugin, DataLoad *loader, NorthService *service) :
	m_plugin(plugin), m_loader(loader), m_service(service), m_shutdown(false), m_paused(false)
{
	m_logger = Logger::getLogger();

	/*
	 * Fianlly start the thread. Everything mus tbe initialsied
	 * before the thread is started
	 */
	m_thread = new thread(startSenderThread, this);
}

/**
 * Destructor for the data sender class
 */
DataSender::~DataSender()
{
	m_logger->info("DataSender shutdown in progress");
	m_shutdown = true;
	m_thread->join();
	delete m_thread;
	m_logger->info("DataSender shutdown complete");
}

/**
 * The sending thread entry point
 */
void DataSender::sendThread()
{
	ReadingSet *readings = nullptr;

	while (!m_shutdown)
	{

		if (readings == nullptr) {

			readings = m_loader->fetchReadings(true);
		}
		if (!readings)
		{
			m_logger->warn(
				"Sending thread closing down after failing to fetch readings");
			return;
		}
		if (readings->getCount() > 0)
		{
			unsigned long lastSent = send(readings);
			if (lastSent)
			{
				m_loader->updateLastSentId(lastSent);

			}
		}
	}
	m_logger->info("Sending thread shutdown");
}

/**
 * Send a block of readings
 *
 * @param readings	The readings to send
 * @return long		The ID of the last reading sent
 */
unsigned long DataSender::send(ReadingSet *readings)
{
	blockPause();
	uint32_t sent = m_plugin->send(readings->getAllReadings());
	releasePause();
	unsigned long lastSent = readings->getReadingId(sent);

	if (sent > 0)
	{
		releasePause();
		lastSent = readings->getLastId();

		// Update asset tracker table/cache, if required
		vector<Reading *> *vec = readings->getAllReadingsPtr();

		for (vector<Reading *>::iterator it = vec->begin(); it != vec->end(); ++it)
		{
			Reading *reading = *it;

			if (reading->getId() <= lastSent)
			{

				AssetTrackingTuple tuple(m_service->getName(), m_service->getPluginName(), reading->getAssetName(), "Egress");
				if (!AssetTracker::getAssetTracker()->checkAssetTrackingCache(tuple))
				{
					AssetTracker::getAssetTracker()->addAssetTrackingTuple(tuple);
					m_logger->info("sendDataThread:  Adding new asset tracking tuple - egress: %s", tuple.assetToString().c_str());
				}
			}
			else
			{
				break;
			}
		}
		m_loader->updateStatistics(sent);
		return lastSent;
	}
	return 0;
}

/**
 * Cause the data sender process to pause sending data until a corresponding release call is made.
 *
 * This call does not block until release is called, but does block until the current
 * send completes.
 *
 * Called by external classes that want to prevent interaction
 * with the north plugin.
 */
void DataSender::pause()
{
	unique_lock<mutex> lck(m_pauseMutex);
	while (m_sending)
	{
		m_pauseCV.wait(lck);
	}
	m_paused = true;
}

/**
 * Release the paused data sender thread
 *
 * Called by external classes that want to release interaction
 * with thew north plugin.
 */
void DataSender::release()
{
	unique_lock<mutex> lck(m_pauseMutex);
	m_paused = false;
	m_pauseCV.notify_all();
}

/**
 * Check if we have paused the sending of data
 *
 * Called before we interact with the north plugin by the
 * DataSender class
 */
void DataSender::blockPause()
{
	unique_lock<mutex> lck(m_pauseMutex);
	while (m_paused)
	{
		m_pauseCV.wait(lck);
	}
	m_sending = true;
}

/*
 * Release the block on pausing the sender
 *
 * Called after we interact with the north plugin by the
 * DataSender class
 */
void DataSender::releasePause()
{
	unique_lock<mutex> lck(m_pauseMutex);
	m_sending = false;
	m_pauseCV.notify_all();
}
