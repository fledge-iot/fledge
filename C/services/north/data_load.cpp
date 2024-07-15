/*
 * Fledge North Service Data Loading.
 *
 * Copyright (c) 2020 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch, Massimiliano Pinto
 */

#include <data_load.h>
#include <north_service.h>

#define INITIAL_BLOCK_WAIT	10
#define MAX_WAIT_PERIOD		200

using namespace std;

static void threadMain(void *arg)
{
	DataLoad *dl = (DataLoad *)arg;
	dl->loadThread();
}

/**
 * DataLoad Constructor
 *
 * Create and start the loading thread
 */
DataLoad::DataLoad(const string& name, long streamId, StorageClient *storage) : 
	m_name(name), m_streamId(streamId), m_storage(storage), m_shutdown(false),
	m_readRequest(0), m_dataSource(SourceReadings), m_pipeline(NULL), m_perfMonitor(NULL),
	m_prefetchLimit(2)
{
	m_blockSize = DEFAULT_BLOCK_SIZE;

	if (m_streamId == 0)
	{
		m_streamId = createNewStream();
	}
	m_nextStreamUpdate = 1;
	m_streamUpdate = 1;
	m_lastFetched = getLastSentId();
	m_flushRequired = false;
	m_thread = new thread(threadMain, this);
	loadFilters(name);
}

/**
 * DataLoad destructor
 *
 * Shutdown and wait for the loading thread
 */
DataLoad::~DataLoad()
{
	// Request the loading thread to shutdown and wait for it
	Logger::getLogger()->info("Data load shutdown in progress");
	m_shutdown = true;
	m_cv.notify_all();
	m_fetchCV.notify_all();
	m_thread->join();
	delete m_thread;
	if (m_pipeline)
	{
		m_pipeline->cleanupFilters(m_name);
		delete m_pipeline;
	}
	if (m_flushRequired)
	{
		flushLastSentId();
	}
	// Clear out the queue of readings
	unique_lock<mutex> lck(m_qMutex);	// Should not need to do this
	while (! m_queue.empty())
	{
		ReadingSet *readings = m_queue.front();
		delete readings;
		m_queue.pop_front();
	}
	Logger::getLogger()->info("Data load shutdown complete");
}

/**
 * External call to shutdown the north service
 */
void DataLoad::shutdown()
{
	m_shutdown = true;
	m_cv.notify_all();
	m_fetchCV.notify_all();
}

/**
 * External call to restart the north service
 */
void DataLoad::restart()
{
	shutdown();
}

/**
 * Set the source of data for the service
 *
 * @param source	The data source
 */
bool DataLoad::setDataSource(const string& source)
{
	if (source.compare("statistics") == 0) {
		m_dataSource = SourceStatistics;
		m_lastFetched = 0;	// Reset on source change
	}
	else if (source.compare("readings") == 0) {
		m_dataSource = SourceReadings;
		m_lastFetched = 0;	// Reset on source change
	}
	else if (source.compare("audit") == 0) {
		m_dataSource = SourceAudit;
		m_lastFetched = 0;	// Reset on source change
	}
	else
	{
		Logger::getLogger()->error("Unsupported source '%s' for north service '%s'",
				source.c_str(), m_name.c_str());
		return false;
	}
	return true;
}

/**
 * The background thread that loads data from the database
 */
void DataLoad::loadThread()
{
	while (!m_shutdown)
	{
		unsigned int block = waitForReadRequest();
		while (m_queue.size() < m_prefetchLimit)	// Read another block if we have less than 
		       						// the prefetch limit already queued
			readBlock(block);
	}
}

/**
 * Wait for a read request to be made. Read requests come from consumer
 * threads calling the triggerRead call that will cause a block of reading
 * data (or whatever the source of data is) to be added to the reading
 * buffer.
 *
 * @return int	The size of the block to read
 */
unsigned int DataLoad::waitForReadRequest()
{
	unique_lock<mutex> lck(m_mutex);
	while (m_shutdown == false && m_readRequest == 0)
	{
		m_cv.wait(lck);
	}
	unsigned int rval =  m_readRequest;
	m_readRequest = 0;
	Logger::getLogger()->debug("DataLoad received read request for %d readings", rval);
	return rval;
}

/**
 * Trigger the loading thread to read a block of data. This is called by
 * any thread to request that data be added to the buffer ready for collection.
 */
void DataLoad::triggerRead(unsigned int blockSize)
{
	unique_lock<mutex> lck(m_mutex);
	m_readRequest = blockSize;
	m_cv.notify_all();
}

/**
 * Read a block of readings, statistics or audit date  from the storage service
 *
 * @param blockSize	The number of readings to fetch
 */
void DataLoad::readBlock(unsigned int blockSize)
{
	int n_waits = 0;
	unsigned int waitPeriod = INITIAL_BLOCK_WAIT;
	do
	{
		ReadingSet* readings = nullptr;
		try
		{
			switch (m_dataSource)
			{
				case SourceReadings:
					// Logger::getLogger()->debug("Fetch %d readings from %d", blockSize, m_lastFetched + 1);
					readings = m_storage->readingFetch(m_lastFetched + 1, blockSize);
					break;
				case SourceStatistics:
					readings = fetchStatistics(blockSize);
					break;
				case SourceAudit:
					readings = fetchAudit(blockSize);
					break;
				default:
					Logger::getLogger()->fatal("Bad source for data to send");
					break;
			}
		}
		catch (ReadingSetException* e)
		{
			// Ignore, the exception has been reported in the layer below
			// readings may contain erroneous data, clear it
			readings = nullptr;
		}
		catch (exception& e)
		{
			// Ignore, the exception has been reported in the layer below
			// readings may contain erroneous data, clear it
			readings = nullptr;
		}
		if (readings && readings->getCount())
		{
			m_lastFetched = readings->getLastId();
			Logger::getLogger()->debug("DataLoad::readBlock(): Got %lu readings from storage client, updated m_lastFetched=%lu", 
							readings->getCount(), m_lastFetched);
			bufferReadings(readings);
			if (m_perfMonitor)
			{
				m_perfMonitor->collect("No of waits for data", n_waits);
				m_perfMonitor->collect("Block utilisation %", (long)((readings->getCount() * 100) / blockSize));
			}
			return;
		}
		else if (readings)
		{
			// Delete the empty readings set
			delete readings;
		}
		else
		{
			// Logger::getLogger()->debug("DataLoad::readBlock(): No readings available");
		}
		if (!m_shutdown)
		{
			// TODO improve this
			this_thread::sleep_for(chrono::milliseconds(waitPeriod));
			waitPeriod *= 2;
			if (waitPeriod > MAX_WAIT_PERIOD)
				waitPeriod = MAX_WAIT_PERIOD;
			n_waits++;
		}
	} while (m_shutdown == false);
}

/**
 * Fetch data from the statistics history table
 *
 * @param blockSize	Number of records to fetch
 * @return ReadingSet*	A set of readings
 */
ReadingSet *DataLoad::fetchStatistics(unsigned int blockSize)
{
	const Condition conditionId(GreaterThan);
	// WHERE id > lastId
	Where* wId = new Where("id", conditionId, to_string(m_lastFetched + 1));
	vector<Returns *> columns;
	// Add colums and needed aliases
	columns.push_back(new Returns("id"));
	columns.push_back(new Returns("key", "asset_code"));
	columns.push_back(new Returns("ts"));

	Returns *tmpReturn = new Returns("history_ts", "user_ts");
	tmpReturn->timezone("utc");
	columns.push_back(tmpReturn);

	columns.push_back(new Returns("value"));
	// Build the query with fields, aliases and where
	Query qStatistics(columns, wId);
	// Set limit
	qStatistics.limit(blockSize);
	// Set sort
	Sort* sort = new Sort("id");
	qStatistics.sort(sort);

	// Query the statistics_history table and get a ReadingSet result
	return m_storage->queryTableToReadings("statistics_history", qStatistics);
}

/**
 * Fetch data from the audit log table
 *
 * @param blockSize	Number of records to fetch
 * @return ReadingSet*	A set of readings
 */
ReadingSet *DataLoad::fetchAudit(unsigned int blockSize)
{
	const Condition conditionId(GreaterThan);
	// WHERE id > lastId
	Where* wId = new Where("id", conditionId, to_string(m_lastFetched + 1));
	vector<Returns *> columns;
	// Add colums and needed aliases
	columns.push_back(new Returns("id"));
	columns.push_back(new Returns("code", "asset_code"));
	columns.push_back(new Returns("ts"));

	Returns *tmpReturn = new Returns("ts", "user_ts");
	tmpReturn->timezone("utc");
	columns.push_back(tmpReturn);

	columns.push_back(new Returns("log", "reading"));
	// Build the query with fields, aliases and where
	Query qStatistics(columns, wId);
	// Set limit
	qStatistics.limit(blockSize);
	// Set sort
	Sort* sort = new Sort("id");
	qStatistics.sort(sort);

	// Query the audit  table and get a ReadingSet result
	return m_storage->queryTableToReadings("log", qStatistics);
}

/**
 * Get the ID of the last reading that was sent with this service
 */
unsigned long DataLoad::getLastSentId()
{
	const Condition conditionId(Equals);
	string streamId = to_string(m_streamId);
	Where* wStreamId = new Where("id",
				     conditionId,
				     streamId);

	// SELECT * FROM fledge.streams WHERE id = x
	Query qLastId(wStreamId);

	ResultSet* lastObjectId = m_storage->queryTable("streams", qLastId);

	if (lastObjectId != NULL && lastObjectId->rowCount())
	{
		// Get the first row only
		ResultSet::RowIterator it = lastObjectId->firstRow();
		// Access the element
		ResultSet::Row* row = *it;
		if (row)
		{
			// Get column value
			ResultSet::ColumnValue* theVal = row->getColumn("last_object");
			// Set found id
			unsigned long rval = (unsigned long)theVal->getInteger();
			delete lastObjectId;
			return rval;
		}
	}
	// Free result set
	delete lastObjectId;

	return 0;
}

/**
 * Buffer a block of readings. Called after a block of data has been
 * read to add that block to the queue reading for collection by the
 * consuming thread.
 *
 * @param readings	The readings to buffer
 */
void DataLoad::bufferReadings(ReadingSet *readings)
{
	if (m_pipeline)
	{
		FilterPlugin *firstFilter = m_pipeline->getFirstFilterPlugin();
		if (firstFilter)
		{

			// Check whether filters are set before calling ingest
			while (!m_pipeline->isReady())
			{
				Logger::getLogger()->warn("Ingest called before "
									  "filter pipeline is ready");
				std::this_thread::sleep_for(std::chrono::milliseconds(150));
			}
			// Pass readingSet to filter chain
			firstFilter->ingest(readings);
			return;
		}
	}
	unique_lock<mutex> lck(m_qMutex);
	m_queue.push_back(readings);
	if (m_perfMonitor && m_perfMonitor->isCollecting())
	{
		m_perfMonitor->collect("Readings added to buffer", (long)(readings->getCount()));
		m_perfMonitor->collect("Reading sets buffered", (long)(m_queue.size()));
		unsigned long i = 0;
		for (auto& set : m_queue)
			i += set->getCount();
		m_perfMonitor->collect("Total readings buffered", (long)i);
	}
	Logger::getLogger()->debug("Buffered %d readings for north processing", readings->getCount());
	m_fetchCV.notify_all();
}

/**
 * Fetch Readings
 *
 * @param wait		Boolean to determine if the call should block the calling thread
 * @return ReadingSet*	Return a block of readings from the buffer
 */
ReadingSet *DataLoad::fetchReadings(bool wait)
{
	unique_lock<mutex> lck(m_qMutex);
	while (m_queue.empty())
	{
		if (m_perfMonitor && m_perfMonitor->isCollecting())
		{
			m_perfMonitor->collect("No data available to fetch", 1);
		}
		triggerRead(m_blockSize);
		if (wait && !m_shutdown)
		{
			m_fetchCV.wait(lck);
		}
		else
		{
			return NULL;
		}
	}
	ReadingSet *rval = m_queue.front();
	m_queue.pop_front();
	if (m_queue.size() < m_prefetchLimit)	// Read another block if we have less than 5 already queued
	{
		triggerRead(m_blockSize);
	}
	return rval;
}

/**
 * Creates a new stream, it adds a new row into the streams table allocating a new stream id
 *
 * @return newly created stream, 0 otherwise
 */
int DataLoad::createNewStream()
{
int streamId = 0;
InsertValues streamValues;

	streamValues.push_back(InsertValue("description",    m_name));
	streamValues.push_back(InsertValue("last_object",    0));

	if (m_storage->insertTable("streams", streamValues) != 1)
	{
		Logger::getLogger()->error("Failed to insert a row into the streams table");
        }
	else
	{
		// Select the row just created, having description='process name'
		const Condition conditionId(Equals);
		Where* wName = new Where("description", conditionId, m_name);
		Query qName(wName);

		ResultSet *rows = m_storage->queryTable("streams", qName);

		if (rows != NULL && rows->rowCount())
		{
			// Get the first row only
			ResultSet::RowIterator it = rows->firstRow();
			// Access the element
			ResultSet::Row* row = *it;
			if (row)
			{
				// Get column value
				ResultSet::ColumnValue* theVal = row->getColumn("id");
				streamId = (int)theVal->getInteger();
			}
		}
		delete rows;
	}

	NorthService::getMgmtClient()->setCategoryItemValue(m_name, "streamId", to_string(streamId));
	return streamId;
}

/**
 * Update the last sent ID for our stream
 */
void DataLoad::updateLastSentId(unsigned long id)
{
	m_streamSent = id;
	m_flushRequired = true;
	if (m_nextStreamUpdate-- <= 0)
	{
		flushLastSentId();
		m_nextStreamUpdate = m_streamUpdate;
	}
}

/**
 * Flush the last sent Id to the storeage layer
 */
void DataLoad::flushLastSentId()
{
	const Condition condition(Equals);
	Where where("id", condition, to_string(m_streamId));
	InsertValues lastId;

	lastId.push_back(InsertValue("last_object", (long)m_streamSent));
	m_storage->updateTable("streams", lastId, where);
}


/**
 * Load filter plugins
 *
 * Filters found in configuration are loaded
 * and add to the data load class instance
 *
 * @param categoryName	Configuration category name
 * @return		True if filters were loaded and initialised
 *			or there are no filters
 *			False with load/init errors
 */
bool DataLoad::loadFilters(const string& categoryName)
{
	Logger::getLogger()->info("loadFilters: categoryName=%s", categoryName.c_str());
	/*
	 * We do everything to setup the pipeline using a local FilterPipeline and then assign it
	 * to the service m_filterPipeline once it is setup to guard against access to the pipeline
	 * during setup.
	 * This should not be an issue if the mutex is held, however this approach lessens the risk
	 * in the case of this routine being called when the mutex is not held and ensure m_filterPipeline
	 * only ever points to a fully configured filter pipeline.
	 */
	ManagementClient *management = NorthService::getMgmtClient();
	lock_guard<mutex> guard(m_pipelineMutex);
	FilterPipeline *filterPipeline = new FilterPipeline(management, *m_storage, m_name);
	
	// Try to load filters:
	if (!filterPipeline->loadFilters(categoryName))
	{
		// Return false on any error
		return false;
	}

	// Set up the filter pipeline
	bool rval = filterPipeline->setupFiltersPipeline((void *)passToOnwardFilter, (void *)pipelineEnd, this);
	if (rval)
	{
		m_pipeline = filterPipeline;
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
void DataLoad::passToOnwardFilter(OUTPUT_HANDLE *outHandle,
				READINGSET *readingSet)
{
	// Get next filter in the pipeline
	FilterPlugin *next = (FilterPlugin *)outHandle;
	// Pass readings to next filter
	next->ingest(readingSet);
}

/**
 * Use the current readings (they have been filtered
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
 * @param outHandle     Pointer to DataLoad class
 * @param readingSet    Filtered reading set being added to Ingest::m_data
 */
void DataLoad::pipelineEnd(OUTPUT_HANDLE *outHandle,
			     READINGSET *readingSet)
{

	DataLoad *load = (DataLoad *)outHandle;
	std::vector<Reading *>* vecPtr = readingSet->getAllReadingsPtr();
    unsigned long lastReadingId = 0;

    for(auto rdngPtrItr = vecPtr->crbegin(); rdngPtrItr != vecPtr->crend(); rdngPtrItr++)
    {
        if((*rdngPtrItr)->hasId()) // only consider valid reading IDs
        {
            lastReadingId = (*rdngPtrItr)->getId();
            break;
        }
    }
    
    Logger::getLogger()->debug("DataLoad::pipelineEnd(): readingSet->getCount()=%d, lastReadingId=%lu, " 
                                "load->m_lastFetched=%lu",
                                  readingSet->getCount(), lastReadingId, load->m_lastFetched);
    
	// Special case when all readings are filtered out 
	// or new readings are appended by filter with id 0
	if ((readingSet->getCount() == 0) || (lastReadingId == 0))
	{
	    Logger::getLogger()->debug("DataLoad::pipelineEnd(): updating with load->updateLastSentId(%d)", 
	                                load->m_lastFetched);
		load->updateLastSentId(load->m_lastFetched);
	}

	unique_lock<mutex> lck(load->m_qMutex);
	load->m_queue.push_back(readingSet);
	load->m_fetchCV.notify_all();
}

/**
 * Configuration change for one of the filters or to the pipeline.
 *
 * @param category	The name of the configuration category
 * @param newConfig	The new category contents
 */
void DataLoad::configChange(const string& category, const string& newConfig)
{
	Logger::getLogger()->debug("DataLoad::configChange(): category=%s, newConfig=%s", category.c_str(), newConfig.c_str());
	if (category == m_name) 
	{
		/**
		 * The category that has changed is the one for the north service itself.
		 * The only items that concerns us here is the filter item that defines
		 * the filter pipeline and the data source. If the item is the filter pipeline
		 * we extract that item and check to see if it defines a pipeline that is
		 * different to the one we currently have.
		 *
		 * If it is the filter pipeline we destroy the current pipeline and create a new one.
		 */
		ConfigCategory config("tmp", newConfig);
		if (config.itemExists("source"))
		{
			setDataSource(config.getValue("source"));
		}
		string newPipeline = "";
		if (config.itemExists("filter"))
		{
		      newPipeline  = config.getValue("filter");
		}

		{
			lock_guard<mutex> guard(m_pipelineMutex);
			if (m_pipeline)
			{
				if (newPipeline == "" ||
				    m_pipeline->hasChanged(newPipeline) == false)
				{
					Logger::getLogger()->info("DataLoad::configChange(): "
								  "filter pipeline is not set or "
								  "it hasn't changed");
					return;
				}
				/* The new filter pipeline is different to what we have already running
				 * So remove the current pipeline and recreate.
			 	 */
				Logger::getLogger()->info("DataLoad::configChange(): "
							  "filter pipeline has changed, "
							  "recreating filter pipeline");
				m_pipeline->cleanupFilters(m_name);
				delete m_pipeline;
				m_pipeline = NULL;
			}
		}

		/*
		 * We have to setup a new pipeline to match the changed configuration.
		 * Release the lock before reloading the filters as this will acquire
		 * the lock again
		 */
		loadFilters(category);

		lock_guard<mutex> guard(m_pipelineMutex);
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
		Logger::getLogger()->info("DataLoad::configChange(): change to config of some filter(s)");
		lock_guard<mutex> guard(m_pipelineMutex);
		if (m_pipeline)
		{
			m_pipeline->configChange(category, newConfig);
		}
	}
}
