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
	m_plugin(plugin), m_loader(loader), m_service(service), m_shutdown(false)
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
	m_shutdown = true;
	m_thread->join();
	delete m_thread;
}

/**
 * The sending thread entry point
 */
void DataSender::sendThread()
{
	while (!m_shutdown)
	{
		ReadingSet *readings = m_loader->fetchReadings(true);
		if (!readings)
		{
			m_logger->warn(
				"Sending thread closing down after failing to fetch readings");
			return;
		}
		unsigned long lastSent = send(readings);
		if (lastSent)
		{
			m_loader->updateLastSentId(lastSent);

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
						Logger::getLogger()->info("sendDataThread:  Adding new asset tracking tuple - egress: %s", tuple.assetToString().c_str());
					}
				}
				else
				{
					break;
				}
			}
		}
		delete readings;
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
	uint32_t sent = m_plugin->send(readings->getAllReadings());
	m_loader->updateStatistics(sent);
	return readings->getLastId();
}
