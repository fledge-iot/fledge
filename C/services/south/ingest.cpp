/*
 * Fledge readings ingest.
 *
 * Copyright (c) 2018 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch, Massimiliano Pinto, Amandeep Singh Arora
 */
#include <ingest.h>
#include <reading.h>
#include <config_handler.h>
#include <thread>
#include <logger.h>
#include <set>

using namespace std;

/**
 * Thread to process the ingest queue and send the data
 * to the storage layer.
 */
static void ingestThread(Ingest *ingest)
{
	while (! ingest->isStopping())
	{
		if (ingest->running())
		{
			ingest->waitForQueue();
			ingest->processQueue();
		}
		else
		{
			std::this_thread::sleep_for(std::chrono::milliseconds(100));
		}
	}
}

/**
 * Thread to update statistics table in DB
 */
static void statsThread(Ingest *ingest)
{
	while (ingest->running())
	{
		ingest->updateStats();
	}
}

/**
 * Create a row for given assetName in statistics DB table, if not present already
 * The key checked/created in the table is "<assetName>"
 * 
 * @param assetName     Asset name for the plugin that is sending readings
 * @return int		Return -1 on error, 0 if not required or 1 if the entry exists
 */
int Ingest::createStatsDbEntry(const string& assetName)
{
	if (m_statisticsOption == STATS_SERVICE)
	{
		// No asset stats required
		return 0;
	}
	// Prepare fledge.statistics update
	string statistics_key = assetName;
	for (auto & c: statistics_key) c = toupper(c);
	
	// SELECT * FROM fledge.statiatics WHERE key = statistics_key
	const Condition conditionKey(Equals);
	Where *wKey = new Where("key", conditionKey, statistics_key);
	Query qKey(wKey);

	ResultSet* result = 0;
	try
	{
		// Query via storage client
		result = m_storage.queryTable("statistics", qKey);

		if (!result->rowCount())
		{
			// Prepare insert values for insertTable
			InsertValues newStatsEntry;
			newStatsEntry.push_back(InsertValue("key", statistics_key));
			newStatsEntry.push_back(InsertValue("description", string("Readings received from asset ")+assetName));
			// Set "value" field for insert using the JSON document object
			newStatsEntry.push_back(InsertValue("value", 0));
			newStatsEntry.push_back(InsertValue("previous_value", 0));

			// Do the insert
			if (!m_storage.insertTable("statistics", newStatsEntry))
			{
				m_logger->error("%s:%d : Insert new row into statistics table failed, newStatsEntry='%s'", __FUNCTION__, __LINE__, newStatsEntry.toJSON().c_str());
				delete result;
				return -1;
			}
		}
		delete result;
	}
	catch (...)
	{
		m_logger->error("%s:%d : Unable to create new row in statistics table with key='%s'", __FUNCTION__, __LINE__, statistics_key.c_str());
		return -1;
	}
	return 1;
}

/**
 * Create a row for service in the statistics DB table, if not present already
 * 
 */
int Ingest::createServiceStatsDbEntry()
{
	if (m_statisticsOption == STATS_ASSET)
	{
		// No service stats required
		return 0;
	}
	// SELECT * FROM fledge.configuration WHERE key = categoryName
	const Condition conditionKey(Equals);
	Where *wKey = new Where("key", conditionKey, m_serviceName + INGEST_SUFFIX);
	Query qKey(wKey);

	ResultSet* result = 0;
	try
	{
		// Query via storage client
		result = m_storage.queryTable("statistics", qKey);

		if (!result->rowCount())
		{
			// Prepare insert values for insertTable
			InsertValues newStatsEntry;
			newStatsEntry.push_back(InsertValue("key", m_serviceName + INGEST_SUFFIX));
			newStatsEntry.push_back(InsertValue("description", string("Readings received from service ")+ m_serviceName));
			// Set "value" field for insert using the JSON document object
			newStatsEntry.push_back(InsertValue("value", 0));
			newStatsEntry.push_back(InsertValue("previous_value", 0));

			// Do the insert
			if (!m_storage.insertTable("statistics", newStatsEntry))
			{
				m_logger->error("%s:%d : Insert new row into statistics table failed, newStatsEntry='%s'", __FUNCTION__, __LINE__, newStatsEntry.toJSON().c_str());
				delete result;
				return -1;
			}
		}
		delete result;
	}
	catch (...)
	{
		m_logger->error("%s:%d : Unable to create new row in statistics table with key='%s'", __FUNCTION__, __LINE__, m_serviceName.c_str());
		return -1;
	}
	return 0;
}
/**
 * Update statistics for this south service. Successfully processed 
 * readings are reflected against plugin asset name and READINGS keys.
 * Discarded readings stats are updated against DISCARDED key.
 */
void Ingest::updateStats()
{
	unique_lock<mutex> lck(m_statsMutex);
	if (m_running) // don't wait on condition variable if plugin/ingest is being shutdown
		m_statsCv.wait_for(lck, std::chrono::seconds(FLUSH_STATS_INTERVAL));

	if (statsPendingEntries.empty())
	{
		return;
	}

	int readings=0;
	vector<pair<ExpressionValues *, Where *>> statsUpdates;
	string key;
	const Condition conditionStat(Equals);
	
	for (auto it = statsPendingEntries.begin(); it != statsPendingEntries.end(); ++it)
	{
		if (statsDbEntriesCache.find(it->first) == statsDbEntriesCache.end())
		{
			if (createStatsDbEntry(it->first) > 0)
			{
				statsDbEntriesCache.insert(it->first);
			}
		}
		
		if (it->second)
		{
			if (m_statisticsOption == STATS_BOTH || m_statisticsOption == STATS_ASSET)
			{
				// Prepare fledge.statistics update
				key = it->first;
				for (auto & c: key) c = toupper(c);

				// Prepare "WHERE key = name
				Where *wPluginStat = new Where("key", conditionStat, key);

				// Prepare value = value + inc
				ExpressionValues *updateValue = new ExpressionValues;
				updateValue->push_back(Expression("value", "+", (int) it->second));

				statsUpdates.emplace_back(updateValue, wPluginStat);
			}
			readings += it->second;
		}
	}

	if (readings)
	{
		Where *wPluginStat = new Where("key", conditionStat, "READINGS");
		ExpressionValues *updateValue = new ExpressionValues;
		updateValue->push_back(Expression("value", "+", (int) readings));
		statsUpdates.emplace_back(updateValue, wPluginStat);

		if (m_statisticsOption == STATS_BOTH || m_statisticsOption == STATS_SERVICE)
		{
			Where *wPluginStat = new Where("key", conditionStat, m_serviceName + INGEST_SUFFIX);
			ExpressionValues *updateValue = new ExpressionValues;
			updateValue->push_back(Expression("value", "+", (int) readings));
			statsUpdates.emplace_back(updateValue, wPluginStat);
		}
	}
	if (m_discardedReadings)
	{
		Where *wPluginStat = new Where("key", conditionStat, "DISCARDED");
		ExpressionValues *updateValue = new ExpressionValues;
		updateValue->push_back(Expression("value", "+", (int) m_discardedReadings));
		statsUpdates.emplace_back(updateValue, wPluginStat);
 	}
	
	try {
		int rv = m_storage.updateTable("statistics", statsUpdates);
		
		if (rv < 0)
		{
			if (++m_statsUpdateFails > STATS_UPDATE_FAIL_THRESHOLD)
			{
				Logger::getLogger()->warn("Update of statistics failure has persisted, attempting recovery");
				createServiceStatsDbEntry();
				statsDbEntriesCache.clear();
				m_statsUpdateFails = 0;
			}
			else if (m_statsUpdateFails == 1)
			{
				Logger::getLogger()->warn("Update of statistics failed");
			}
			else
			{
				Logger::getLogger()->warn("Update of statistics still failing");
			}
		}
		else
		{
			m_discardedReadings = 0;
			statsPendingEntries.clear();
		}
	}
	catch (...) {
		Logger::getLogger()->info("%s:%d : Statistics table update failed, will retry on next iteration", __FUNCTION__, __LINE__);
	}
	for (auto it = statsUpdates.begin(); it != statsUpdates.end(); ++it)
	{
		delete it->first;
		delete it->second;
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
 */
Ingest::Ingest(StorageClient& storage,
		const std::string& serviceName,
		const std::string& pluginName,
		ManagementClient *mgmtClient) :
			m_storage(storage),
			m_serviceName(serviceName),
			m_pluginName(pluginName),
			m_mgtClient(mgmtClient),
			m_failCnt(0),
			m_storageFailed(false),
			m_storesFailed(0),
			m_statisticsOption(STATS_BOTH),
			m_highWater(0)
{
	m_shutdown = false;
	m_running = true;
	m_queue = new vector<Reading *>();
	m_logger = Logger::getLogger();
	m_data = NULL;
	m_discardedReadings = 0;
	m_highLatency = false;

	// populate asset and storage asset tracking cache
	AssetTracker *as = AssetTracker::getAssetTracker();
	as->populateAssetTrackingCache(m_pluginName, "Ingest");
	as->populateStorageAssetTrackingCache();

	// Create the stats entry for the service
	createServiceStatsDbEntry();

	m_filterPipeline = NULL;

	m_deprecated = NULL;

	m_deprecatedAgeOut = 0;
	m_deprecatedAgeOutStorage = 0;
}

/**
 * Start the ingest threads
 *
 * @param timeout	Maximum time before sending a queue of readings in milliseconds
 * @param threshold	Length of queue before sending readings
 */
void Ingest::start(long timeout, unsigned int threshold)
{
	m_timeout = timeout;
	m_queueSizeThreshold = threshold;
	m_thread = new thread(ingestThread, this);
	m_statsThread = new thread(statsThread, this);
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
	m_shutdown = true;
	m_running = false;
	
	// Cleanup filters
	{
		lock_guard<mutex> guard(m_pipelineMutex);
		if (m_filterPipeline)
		{
			m_filterPipeline->setShuttingDown();
			m_filterPipeline->cleanupFilters(m_serviceName);  // filter's shutdown API could potentially try to feed some new readings using the async ingest mechnanism
		}
	}
	
	m_cv.notify_one();
	m_thread->join();
	processQueue();
	m_statsCv.notify_one();
	m_statsThread->join();
	updateStats();
	// Cleanup and readings left in the various queues
	for (auto& reading : *m_queue)
	{
		delete reading;
	}
	delete m_queue;
	for (auto& q : m_resendQueues)
	{
		for (auto& rq : *q)
		{
			delete rq;
		}
		delete q;
	}
	while (m_fullQueues.size() > 0)
	{
		vector<Reading *> *q = m_fullQueues.front();
		for (auto& rq : *q)
		{
			delete rq;
		}
		delete q;
		m_fullQueues.pop();
	}
	delete m_thread;
	delete m_statsThread;

	// Delete filter pipeline
	{
		lock_guard<mutex> guard(m_pipelineMutex);
		if (m_filterPipeline)
			delete m_filterPipeline;
	}

	if (m_deprecated)
		delete m_deprecated;
}

/**
 * Check if the ingest process is still running.
 * This becomes false when the service is shutdown
 * and is used to allow the queue to drain and then
 * the processing routine to terminate.
 */
bool Ingest::running()
{
	lock_guard<mutex> guard(m_pipelineMutex);
	return m_running;
}

/**
 * Check if a shutdown is requested
 */
bool Ingest::isStopping()
{
	return m_shutdown;
}

/**
 * Add a reading to the reading queue
 *
 * @param reading	The single reading to ingest
 */
void Ingest::ingest(const Reading& reading)
{
vector<Reading *> *fullQueue = 0;

	{
		lock_guard<mutex> guard(m_qMutex);
		m_queue->emplace_back(new Reading(reading));
		if (m_queue->size() >= m_queueSizeThreshold || m_running == false)
		{
			fullQueue = m_queue;
			m_queue = new vector<Reading *>;
		}
	}
	if (fullQueue)
	{
		lock_guard<mutex> guard(m_fqMutex);
		m_fullQueues.push(fullQueue);
	}
	if (m_fullQueues.size())
		m_cv.notify_all();
	m_performance->collect("queueLength", (long)queueLength());
}

/**
 * Add a set of readings to the reading queue
 *
 * @param vec	A vector of readings to ingest
 */
void Ingest::ingest(const vector<Reading *> *vec)
{
vector<Reading *> *fullQueue = 0;
size_t qSize;
unsigned int nFullQueues = 0;

	{
		lock_guard<mutex> guard(m_qMutex);
		
		// Get the readings in the set
		for (auto & rdng : *vec)
		{
			m_queue->emplace_back(rdng);
		}
		if (m_queue->size() >= m_queueSizeThreshold || m_running == false)
		{
			fullQueue = m_queue;
			m_queue = new vector<Reading *>;
		}
		qSize = m_queue->size();
	}
	if (fullQueue)
	{
		lock_guard<mutex> guard(m_fqMutex);
		m_fullQueues.push(fullQueue);
		nFullQueues = m_fullQueues.size();
	}
	else
	{
		lock_guard<mutex> guard(m_fqMutex);
		nFullQueues = m_fullQueues.size();
	}
	if (nFullQueues != 0 || qSize > m_queueSizeThreshold * 3 / 4)
	{
		m_cv.notify_all();
	}
	m_performance->collect("queueLength", (long)queueLength());
	m_performance->collect("ingestCount", (long)vec->size());
}

/**
 * Work out how long to wait based on age of oldest queued reading
 * We do this in a separate function so that we can lock the qMutex
 * to access the oldest element in the queue
 *
 * @return the time to wait
 */
long Ingest::calculateWaitTime()
{
	long timeout = m_timeout;
	lock_guard<mutex> guard(m_qMutex);
	if (!m_queue->empty())
	{
		Reading *reading = (*m_queue)[0];
		struct timeval tm, now;
		reading->getUserTimestamp(&tm);
		gettimeofday(&now, NULL);
		long ageMS = (now.tv_sec - tm.tv_sec) * 1000 +
			(now.tv_usec - tm.tv_usec) / 1000;
		timeout = m_timeout - ageMS;
	}
	return timeout;
}

/**
 * Wait for a period of time to allow the queue to build
 */
void Ingest::waitForQueue()
{
	if (m_fullQueues.size() > 0 || m_resendQueues.size() > 0)
		return;
	if (m_running && m_queue->size() < m_queueSizeThreshold)
	{
		long timeout = calculateWaitTime();
		if (timeout > 0)
		{
			mutex mtx;
			unique_lock<mutex> lck(mtx);
			m_cv.wait_for(lck,chrono::milliseconds((3 * timeout) / 4));
		}
	}
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
	do {
		/*
		 * If we have some data that has been previously filtered but failed to send,
		 * then first try to send that data.
		 */
		while (m_resendQueues.size() > 0)
		{
			vector<Reading *> *q = *m_resendQueues.begin();
			if (m_storage.readingAppend(*q) == false)
			{
				if (!m_storageFailed)
					m_logger->info("Still unable to resend buffered data, leaving on resend queue.");
				m_storageFailed = true;
				m_storesFailed++;
				m_failCnt++;
				if (m_failCnt > 5)
				{
					m_logger->info("Too many failures with block of readings. Removing readings from block");
					for (int cnt = 5; cnt > 0 && q->size() > 0; cnt--)
					{
						Reading *reading = q->front();
						m_logger->info("Remove reading: %s",
								reading->toJSON().c_str());
						delete reading;
						q->erase(q->begin());
						logDiscardedStat();
					}
					m_performance->collect("removedFromQueue", 5);
					if (q->size() == 0)
					{
						delete q;
						m_resendQueues.erase(m_resendQueues.begin());
					}
					m_failCnt = 0;
				}
			}
			else
			{

				m_performance->collect("storedReadings", (long int)(q->size()));
				if (m_storageFailed)
				{
					m_logger->warn("Storage operational after %d failures", m_storesFailed);
					m_storageFailed = false;
					m_storesFailed = 0;
				}
				m_failCnt = 0;
				std::map<std::string, int>		statsEntriesCurrQueue;
				AssetTracker *tracker = AssetTracker::getAssetTracker();
				if (tracker == nullptr)
                                {
                                        Logger::getLogger()->error("%s could not initialize asset tracker",
								__FUNCTION__);
					return;
                                }

				string lastAsset = "";
				int *lastStat = NULL;
				std::map <std::string , std::set<std::string> > assetDatapointMap;

				for (vector<Reading *>::iterator it = q->begin();
							 it != q->end(); ++it)
				{
					Reading *reading = *it;
					string assetName = reading->getAssetName();
                                        const std::vector<Datapoint *> dpVec = reading->getReadingData();
					std::string temp;
					std::set<std::string> tempSet;
					// first sort the individual datapoints 
					// e.g. dp2, dp3, dp1 push them in a set,to make them 
					// dp1,dp2,dp3
                                        for ( auto dp : dpVec)
                                        {
						temp.clear();
                                                temp.append(dp->getName());
						tempSet.insert(temp);
                                        }

					temp.clear();

					// Push them in a set so as to avoid duplication of datapoints
					// a reading of d1, d2, d3 and another d2,d3,d1 , second will be discarded
					//
					for (auto dp: tempSet)
					{
						set<string> &s= assetDatapointMap[assetName];
						if (s.find(dp) == s.end())
						{
							s.insert(dp);
						}
					}

					if (lastAsset.compare(assetName))
					{
						AssetTrackingTuple tuple(m_serviceName,
									m_pluginName,
									assetName,
									"Ingest");

						// Check Asset record exists
						AssetTrackingTuple* res = tracker->findAssetTrackingCache(tuple);
						if (res == NULL)
						{
							// Record non in cache, add it
							tracker->addAssetTrackingTuple(tuple);
						}
						else
						{
							// Possibly Un-deprecate asset tracking record
							unDeprecateAssetTrackingRecord(res,
											assetName,
											"Ingest");
						}
						lastAsset = assetName;
						lastStat = &(statsEntriesCurrQueue[assetName]);
						(*lastStat)++;
					}
					else if (lastStat)
					{
						(*lastStat)++;
					}
					delete reading;
				}

				for (auto itr : assetDatapointMap)
				{
					std::set<string> &s = itr.second;
					unsigned int count = s.size();
					StorageAssetTrackingTuple storageTuple(m_serviceName,
										m_pluginName,
										itr.first,
										"store",
										false,
										"",
										count);

					StorageAssetTrackingTuple *ptr = &storageTuple;

					// Update SAsset Tracker database and cache
					tracker->updateCache(s, ptr);
				}

				delete q;
				m_resendQueues.erase(m_resendQueues.begin());
				unique_lock<mutex> lck(m_statsMutex);
				for (auto &it : statsEntriesCurrQueue)
				{
					statsPendingEntries[it.first] += it.second;
				}
			}
		}

		{
			lock_guard<mutex> fqguard(m_fqMutex);
			if (m_fullQueues.empty())
			{
				if (!m_shutdown)
				{
					// Block of code to execute holding the mutex
					lock_guard<mutex> guard(m_qMutex);
					std::vector<Reading *> *newQ = new vector<Reading *>;
					m_data = m_queue;
					m_queue = newQ;
				}
			}
			else
			{
				m_data = m_fullQueues.front();
				m_fullQueues.pop();
			}
		}
		
		/*
		 * Create a ReadingSet from m_data readings if we have filters.
		 *
		 * At this point the m_data vector is cleared so that the only reference to
		 * the readings is in the ReadingSet that is passed along the filter pipeline
		 *
		 * The final filter in the pipeline will pass the ReadingSet back into the
		 * ingest class where it will repopulate the m_data member.
		 *
		 * We lock the filter pipeline here to prevent it being reconfigured whilst we
		 * process the data. We do this because the qMutex is not good enough here as we
		 * do not hold it, by deliberate policy. As we copy the queue holding the qMutex
		 * and then release it to enable more data to be queued while we process the previous
		 * queue via the filter pipeline and up to the storage layer.
		 */
		{
			lock_guard<mutex> guard(m_pipelineMutex);
			if (m_filterPipeline && !m_filterPipeline->isShuttingDown())
			{
				FilterPlugin *firstFilter = m_filterPipeline->getFirstFilterPlugin();
				if (firstFilter)
				{
					// Check whether filters are set before calling ingest
					while (!m_filterPipeline->isReady())
					{
						Logger::getLogger()->warn("Ingest called before "
									  "filter pipeline is ready");
						std::this_thread::sleep_for(std::chrono::milliseconds(150));
					}

					ReadingSet *readingSet = new ReadingSet(m_data);
					m_data->clear();
					// Pass readingSet to filter chain
					firstFilter->ingest(readingSet);

					/*
					 * If filtering removed all the readings then simply clean up m_data and
					 * return.
					 */
					if (m_data->size() == 0)
					{
						delete m_data;
						m_data = NULL;
						return;
					}
				}
			}
		}

		/*
		 * Check the first reading in the list to see if we are meeting the
		 * latency configuration we have been set
		 */
		if (m_data)
		{
			vector<Reading *>::iterator itr = m_data->begin();
			if (itr != m_data->cend())
			{
				Reading *firstReading = *itr;
				struct timeval tmFirst, tmNow, dur;
				gettimeofday(&tmNow, NULL);
				firstReading->getUserTimestamp(&tmFirst);
				timersub(&tmNow, &tmFirst, &dur);
				long latency = dur.tv_sec * 1000 + (dur.tv_usec / 1000);
				m_performance->collect("readLatency", latency);
				if (latency > m_timeout && m_highLatency == false)
				{
					m_logger->warn("Current send latency of %ldms exceeds requested maximum latency of %dmS", latency, m_timeout);
					m_highLatency = true;
					m_10Latency = false;
					m_reportedLatencyTime = time(0);
				}
				else if (latency <= m_timeout / 1000 && m_highLatency)
				{
					m_logger->warn("Send latency now within requested limits");
					m_highLatency = false;
				}
				else if (m_highLatency && latency > m_timeout + (m_timeout / 10) && time(0) - m_reportedLatencyTime > 60)
				{
					// Report again every minute if we are outside the latency
					// target by more than 10%
					m_logger->warn("Current send latency of %ldms still significantly exceeds requested maximum latency of %dmS", latency, m_timeout);
					m_reportedLatencyTime = time(0);
				}
				else if (m_highLatency && latency < m_timeout + (m_timeout / 10) && m_10Latency == false)
				{
					m_logger->warn("Send latency of %ldms is now less than 10%% from target", latency);
					m_10Latency = true;
				}
			}
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
		if (m_data && m_data->size())
		{
			if (m_storage.readingAppend(*m_data) == false)
			{
				if (!m_storageFailed)
					m_logger->warn("Failed to write readings to storage layer, queue for resend");
				m_storageFailed = true;
				m_storesFailed++;
				m_performance->collect("resendQueued", (long int)(m_data->size()));
				m_resendQueues.push_back(m_data);
				m_data = NULL;
				m_failCnt = 1;
			}
			else
			{
				m_performance->collect("storedReadings", (long int)(m_data->size()));
				if (m_storageFailed)
				{
					m_logger->warn("Storage operational after %d failures", m_storesFailed);
					m_storageFailed = false;
					m_storesFailed = 0;
				}
				m_failCnt = 0;
				std::map<std::string, int>		statsEntriesCurrQueue;
				// check if this requires addition of a new asset tracker tuple
				// Remove the Readings in the vector
				AssetTracker *tracker = AssetTracker::getAssetTracker();

				string lastAsset;
				int *lastStat = NULL;
				std::map <std::string, std::set<std::string> > assetDatapointMap;

				for (vector<Reading *>::iterator it = m_data->begin(); it != m_data->end(); ++it)
				{
		               	        Reading *reading = *it;
					string	assetName = reading->getAssetName();
					const std::vector<Datapoint *> dpVec = reading->getReadingData();
					std::string temp;
                                        std::set<std::string> tempSet;
                                        // first sort the individual datapoints
                                        // e.g. dp2, dp3, dp1 push them in a set,to make them
                                        // dp1,dp2,dp3
                                        for ( auto dp : dpVec)
                                        {
                                                temp.clear();
                                                temp.append(dp->getName());
                                                tempSet.insert(temp);
                                        }

                                        temp.clear();

                                        // Push them in a set so as to avoid duplication of datapoints
                                        // a reading of d1, d2, d3 and another d2,d3,d1 , second will be discarded
                                        //
                                        for (auto dp: tempSet)
                                        {
                                                set<string> &s= assetDatapointMap[assetName];
                                                if (s.find(dp) == s.end())
                                                {
                                                        s.insert(dp);
                                                }
                                        }

                                        if (lastAsset.compare(assetName))
                                        {
						AssetTrackingTuple tuple(m_serviceName,
									m_pluginName,
									assetName,
									"Ingest");

						// Check Asset record exists
						AssetTrackingTuple* res = tracker->findAssetTrackingCache(tuple);
						if (res == NULL)
						{
							// Record not in cache, add it
							tracker->addAssetTrackingTuple(tuple);
						}
						else
						{
							// Un-deprecate asset tracking record
							unDeprecateAssetTrackingRecord(res,
											assetName,
											"Ingest");
						}

						lastAsset = assetName;
                                                  lastStat = &statsEntriesCurrQueue[assetName];
                                                  (*lastStat)++;
                                          }
                                          else if (lastStat)
                                          {
                                                  (*lastStat)++;
                                          }
                                          // delete reading;

				}
				for( auto & rdng : *m_data)
				{
					delete rdng;
				}
				m_data->clear();

				for (auto itr : assetDatapointMap)
				{
					std::set<string> &s = itr.second;
				        unsigned int count = s.size();
				        StorageAssetTrackingTuple storageTuple(m_serviceName,
										m_pluginName,
										itr.first,
										"store",
										false,
										"",
										count);

					StorageAssetTrackingTuple *ptr = &storageTuple;

					// Update SAsset Tracker database and cache
					tracker->updateCache(s, ptr);
				}

				{
					unique_lock<mutex> lck(m_statsMutex);
					for (auto &it : statsEntriesCurrQueue)
					{
						statsPendingEntries[it.first] += it.second;
					}
				}
			}
		}

		if (m_data)
		{
			delete m_data;
			m_data = NULL;
		}
	} while (! m_fullQueues.empty());
}

/**
 * Load filter plugins
 *
 * Filters found in configuration are loaded
 * and add to the Ingest class instance
 *
 * @param categoryName	Configuration category name
 * @param ingest	The Ingest class reference
 *			Filters are added to m_filters member
 *			False for errors.
 * @return		True if filters were loaded and initialised
 *			or there are no filters
 *			False with load/init errors
 */
bool Ingest::loadFilters(const string& categoryName)
{
	Logger::getLogger()->info("Ingest::loadFilters(): categoryName=%s", categoryName.c_str());
	/*
	 * We do everything to setup the pipeline using a local FilterPipeline and then assign it
	 * to the service m_filterPipeline once it is setup to guard against access to the pipeline
	 * during setup.
	 * This should not be an issue if the mutex is held, however this approach lessens the risk
	 * in the case of this routine being called when the mutex is not held and ensure m_filterPipeline
	 * only ever points to a fully configured filter pipeline.
	 */
	lock_guard<mutex> guard(m_pipelineMutex);
	FilterPipeline *filterPipeline = new FilterPipeline(m_mgtClient, m_storage, m_serviceName);
	
	// Try to load filters:
	if (!filterPipeline->loadFilters(categoryName))
	{
		// Return false on any error
		return false;
	}

	// Set up the filter pipeline
	bool rval = filterPipeline->setupFiltersPipeline((void *)passToOnwardFilter, (void *)useFilteredData, this);
	if (rval)
	{
		m_filterPipeline = filterPipeline;
	}
	else
	{
		Logger::getLogger()->error("Failed to setup the filter pipeline, the filters are not attached to the service");
		filterPipeline->cleanupFilters(categoryName);
	}
	return rval;
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
 * The assumption is that one of two things has happened.
 *
 *	1. The filtering has all been done in place. In which case
 *	the m_data vector is in the ReadingSet passed in here.
 *
 *	2. The filtering has created new ReadingSet in which case
 *	the reading vector must be copied into m_data from the
 *	ReadingSet.
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

	if (ingest->m_data != readingSet->getAllReadingsPtr())
	{
		if (ingest->m_data)
		{
		    // Remove the readings in the vector
		    for(auto & rdngPtr : *(ingest->m_data))
		        delete rdngPtr;

                   ingest->m_data->clear();// Remove any pointers still in the vector
		   delete ingest->m_data;
                   ingest->m_data = readingSet->moveAllReadings();
		}
		else
		{
		    // move reading vector to ingest
		    ingest->m_data = readingSet->moveAllReadings();
		}
	}
	else
	{
	    Logger::getLogger()->info("%s:%d: Input readingSet modified by filter: ingest->m_data=%p, readingSet->getAllReadingsPtr()=%p", 
                                        __FUNCTION__, __LINE__, ingest->m_data, readingSet->getAllReadingsPtr());
	}
	
	readingSet->clear();
	delete readingSet;
}

/**
 * Configuration change for one of the filters or to the pipeline.
 *
 * @param category	The name of the configuration category
 * @param newConfig	The new category contents
 */
void Ingest::configChange(const string& category, const string& newConfig)
{
	Logger::getLogger()->debug("Ingest::configChange(): category=%s, newConfig=%s", category.c_str(), newConfig.c_str());
	if (category == m_serviceName) 
	{
		/**
		 * The category that has changed is the one for the south service itself.
		 * The only item that concerns us here is the filter item that defines
		 * the filter pipeline. We extract that item and check to see if it defines
		 * a pipeline that is different to the one we currently have.
		 *
		 * If it is we destroy the current pipeline and create a new one.
		 */
		ConfigCategory config("tmp", newConfig);
		string newPipeline = "";
		if (config.itemExists("filter"))
		{
		      newPipeline  = config.getValue("filter");
		}

		{
			lock_guard<mutex> guard(m_pipelineMutex);
			if (m_filterPipeline)
			{
				if (newPipeline == "" ||
				    m_filterPipeline->hasChanged(newPipeline) == false)
				{
					Logger::getLogger()->info("Ingest::configChange(): "
								  "filter pipeline is not set or "
								  "it hasn't changed");
					return;
				}
				/* The new filter pipeline is different to what we have already running
				 * So remove the current pipeline and recreate.
			 	 */
				m_running = false;
				Logger::getLogger()->info("Ingest::configChange(): "
							  "filter pipeline has changed, "
							  "recreating filter pipeline");
				m_filterPipeline->cleanupFilters(m_serviceName);
				delete m_filterPipeline;
				m_filterPipeline = NULL;
			}
		}

		/*
		 * We have to setup a new pipeline to match the changed configuration.
		 * Release the lock before reloading the filters as this will acquire
		 * the lock again
		 */
		loadFilters(category);

		// Set m_running holding the lock
		lock_guard<mutex> guard(m_pipelineMutex);
		m_running = true;
	}
	else
	{
		/*
		 * The category is for one fo the filters. We simply call the Filter Pipeline
		 * instance and get it to deal with sending the configuration to the right filter.
		 * This is done holding the pipeline mutex to prevent the pipeline being changed
		 * during this call and also to hold the ingest thread from running the filters
		 * during reconfiguration.
		 */
		Logger::getLogger()->info("Ingest::configChange(): change to config of some filter(s)");
		lock_guard<mutex> guard(m_pipelineMutex);
		if (m_filterPipeline)
		{
			m_filterPipeline->configChange(category, newConfig);
		}
	}
}

/**
 * Return the numebr fo queued readings in the south service
 */
size_t Ingest::queueLength()
{
	size_t	len = m_queue->size();

	// Approximate the amount of data in the full queues
	len += m_fullQueues.size() * m_queueSizeThreshold;
	len += m_resendQueues.size() * m_queueSizeThreshold;

	return len;
}

/**
 * Load an up-to-date AssetTracking record for the given parameters
 * and un-deprecate AssetTracking record it has been found as deprecated
 * Existing cache element is updated
 *
 * @param currentTuple		Current AssetTracking record for given assetName
 * @param assetName		AssetName to fetch from AssetTracking
 * @param event			The event type to fetch
 */
void Ingest::unDeprecateAssetTrackingRecord(AssetTrackingTuple* currentTuple,
					const string& assetName,
					const string& event)
{
	time_t now = time(0);
	if (m_deprecatedAgeOut < now)
	{
		delete m_deprecated;
		m_deprecated = m_mgtClient->getDeprecatedAssetTrackingTuples();
		m_deprecatedAgeOut = now + DEPRECATED_CACHE_AGE;
	}
	if (m_deprecated && m_deprecated->find(assetName))
	{
		// The asset is deprecated possibly
		m_deprecated->remove(assetName);
	}
	else
	{
		// The asset is not believed to be deprecated so return. If
		// it has been deprecated since we last loaded the cache this
		// will leave the asset incorrectly deprecated. This will be
		// resolved next time the cache is reloaded
		return;
	}
	// Get up-to-date Asset Tracking record 
	AssetTrackingTuple* updatedTuple =
			m_mgtClient->getAssetTrackingTuple(
			m_serviceName,
			assetName,
			event);

	bool unDeprecateDataPoints = false;
	if (updatedTuple)
	{
		if (updatedTuple->isDeprecated())
		{
			// Update un-deprecated state in cached object
			currentTuple->unDeprecate();

			m_logger->debug("Asset '%s' is being un-deprecated",
					assetName.c_str());

			// Prepare UPDATE query
			const Condition conditionParams(Equals);
			Where * wAsset = new Where("asset",
						conditionParams,
						assetName);
			Where *wService = new Where("service",
						conditionParams,
						m_serviceName,
						wAsset);
			Where *wEvent = new Where("event",
						conditionParams,
						event,
						wService);

			InsertValues unDeprecated;

			// Set NULL value
			unDeprecated.push_back(InsertValue("deprecated_ts"));
				
			// Update storage with NULL value
			int rv = m_storage.updateTable("asset_tracker",
							unDeprecated,
							*wEvent);

			// Check update operation
			if (rv < 0)
			{
				m_logger->error("Failure while un-deprecating asset '%s'",
						assetName.c_str());
			}
			else
			{
				string audit_details = "{\"asset\" : \"" + assetName +
							"\", \"service\" : \"" + m_serviceName +
							"\", \"event\" : \"" + event + "\"}";
				// Add AuditLog entry
				if (!m_mgtClient->addAuditEntry("ASTUN", "INFORMATION", audit_details))
				{
					m_logger->warn("Failure while adding AuditLog entry " \
							" for un-deprecated asset '%s'",
							assetName.c_str());
				}
				m_logger->info("Asset '%s' has been un-deprecated, event '%s'",
						assetName.c_str(),
						event.c_str());

				unDeprecateDataPoints = true;
			}
		}
	}
	else
	{
		m_logger->error("Failure to get AssetTracking record "
				"for service '%s', asset '%s'",
				m_serviceName.c_str(),
				assetName.c_str());
	}

	delete updatedTuple;

	// Undeprecate all "store" events related to the serviceName and assetName
	if (unDeprecateDataPoints)
	{
		// Prepare UPDATE query
		const Condition conditionParams(Equals);
		Where * wAsset = new Where("asset",
					conditionParams,
					assetName);
		Where *wService = new Where("service",
					conditionParams,
					m_serviceName,
					wAsset);
		Where *wEvent = new Where("event",
					conditionParams,
					"store",
					wService);

		InsertValues unDeprecated;

		// Set NULL value
		unDeprecated.push_back(InsertValue("deprecated_ts"));
        
		// Update storage with NULL value
		int rv = m_storage.updateTable("asset_tracker",
						unDeprecated,
						*wEvent);

		// Check update operation
		if (rv < 0)
		{
			m_logger->error("Failure while un-deprecating asset '%s'",
					assetName.c_str());
		}
		else
		{
			m_logger->info("Asset '%s' has been un-deprecated, event '%s'",
					assetName.c_str(),
					"store");
		}
	}
}

/**
 * Load an up-to-date StorageAssetTracking record for the given parameters
 * and un-deprecate StorageAssetTracking record it has been found as deprecated
 * Existing cache element is updated
 *
 * @param currentTuple          Current StorageAssetTracking record for given assetName
 * @param assetName             AssetName to fetch from AssetTracking
 * @param  datapoints           The datapoints comma separated list
 * @param count			The number of datapoints per asset
 */
void Ingest::unDeprecateStorageAssetTrackingRecord(StorageAssetTrackingTuple* currentTuple,
                                        const string& assetName,
					const string& datapoints,
					const unsigned int& count)
                                        
{
	time_t now = time(0);
	if (m_deprecatedAgeOutStorage < now)
	{
		m_deprecatedAgeOutStorage = now + DEPRECATED_CACHE_AGE;
	}
	else
	{
		// Nothing to do right now
		return;
	}


        // Get up-to-date Asset Tracking record
        StorageAssetTrackingTuple* updatedTuple =
                        m_mgtClient->getStorageAssetTrackingTuple(
                        m_serviceName,
                        assetName,
                        "store", 
			datapoints,
			count);

        vector<string> tokens;
        stringstream dpStringStream(datapoints);
        string temp;
        while(getline(dpStringStream, temp, ','))
        {
                tokens.push_back(temp);
        }

	ostringstream convert;
        convert << "{";
        convert << "\"datapoints\":[";
        for (unsigned int i = 0; i < tokens.size() ; ++i)
        {
		convert << "\"" << tokens[i].c_str() << "\"" ;
                if (i < tokens.size()-1){
	                convert << ",";
                }
        }
        convert << "]," ;
        convert << "\"count\":" << to_string(count).c_str();
        convert << "}";

        if (updatedTuple)
        {
                if (updatedTuple->isDeprecated())
                {

                        // Update un-deprecated state in cached object
                        currentTuple->unDeprecate();

                        m_logger->info("%s:%d, Asset '%s' is being un-deprecated",__FILE__, __LINE__, assetName.c_str());

                        // Prepare UPDATE query
                        const Condition conditionParams(Equals);
                        Where * wAsset = new Where("asset",
                                                conditionParams,
                                                assetName);
                        Where *wService = new Where("service",
                                                conditionParams,
                                                m_serviceName,
                                                wAsset);
                        Where *wEvent = new Where("event",
                                                conditionParams,
                                                "store",
                                                wService);

			Where *wData = new Where("data",
                                                conditionParams,
                                                JSONescape(convert.str()),
                                                wEvent);


			InsertValues unDeprecated;

                        // Set NULL value
                        unDeprecated.push_back(InsertValue("deprecated_ts"));

                        // Update storage with NULL value
                        int rv = m_storage.updateTable("asset_tracker",
                                                        unDeprecated,
                                                        *wData);

                        // Check update operation
                        if (rv < 0)
                        {
                                m_logger->error("%s:%d, Failure while un-deprecating asset '%s'", __FILE__, __LINE__, assetName.c_str());
			}
		}
	}

	if (updatedTuple != nullptr)
		delete updatedTuple;
}

/**
 * Set the statistics option. The statistics collection regime may be one of
 * "per asset", "per service" or "per asset & service".
 *
 * @param option	The desired statistics collection regime
 */
void Ingest::setStatistics(const string& option)
{
	unique_lock<mutex> lck(m_statsMutex);
	if (option.compare("per asset") == 0)
		m_statisticsOption = STATS_ASSET;
	else if (option.compare("per service") == 0)
		m_statisticsOption = STATS_SERVICE;
	else
		m_statisticsOption = STATS_BOTH;
}

/*
 * Returns comma-separated string from set of datapoints
 */
std::string  Ingest::getStringFromSet(const std::set<std::string> &dpSet)
{
	std::string s;
	for (auto itr: dpSet)
	{
		s.append(itr);
		s.append(",");
	}
	// remove the last comma
	if (s[s.size() -1] == ',')
		s.pop_back();
	return s;
}

/**
 * Implement flow control backoff for the async ingest mechanism.
 *
 * The flow control is "soft" in that it will only wait for a maximum
 * amount of time before continuing regardless of the queue length.
 *
 * The mechanism is to have a high water and low water mark. When the queue
 * get longer than the high water mark we wait until the queue drains below
 * the low water mark before proceeding.
 *
 * The wait is done with a backoff algorithm that start at AFC_SLEEP_INCREMENT
 * and doubles each time we have not dropped below the low water mark. It will
 * sleep for a maximum of AFC_SLEEP_MAX before testing again.
 */
void Ingest::flowControl()
{
	if (m_highWater == 0)	// No flow control
	{
		return;
	}
	if (m_highWater < queueLength())
	{
		m_logger->debug("Waiting for ingest queue to drain");
		int total = 0, delay = AFC_SLEEP_INCREMENT;
		while (total < AFC_MAX_WAIT && queueLength() > m_lowWater)
		{
			this_thread::sleep_for(chrono::milliseconds(delay));
			total += delay;
			delay *= 2;
			if (delay > AFC_SLEEP_MAX)
			{
				delay = AFC_SLEEP_MAX;
			}
		}
		m_logger->debug("Ingest queue has %s", queueLength() > m_lowWater
			       	? "failed to drain in sufficient time" : "has drained");
		m_performance->collect("flow controlled", total);
	}
}
