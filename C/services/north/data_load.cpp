/*
 * Fledge North Service Data Loading.
 *
 * Copyright (c) 2020 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */

#include <data_load.h>
#include <north_service.h>

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
	m_readRequest(0), m_dataSource(SourceReadings), m_pipeline(NULL)
{
	if (m_streamId == 0)
	{
		m_streamId = createNewStream();
	}
	m_lastFetched = getLastSentId();
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
	if (m_pipeline)
	{
		m_pipeline->cleanupFilters(m_name);
		delete m_pipeline;
	}
	Logger::getLogger()->info("Data load shutdown complete");
}

/**
 * External call to shutdown
 */
void DataLoad::shutdown()
{
	m_shutdown = true;
	m_cv.notify_all();
	m_fetchCV.notify_all();
}

/**
 * Set the source of data for the service
 *
 * @param source	The data source
 */
bool DataLoad::setDataSource(const string& source)
{
	if (source.compare("statistics") == 0)
		m_dataSource = SourceStatistics;
	else if (source.compare("readings") == 0)
		m_dataSource = SourceReadings;
	else if (source.compare("audit") == 0)
		m_dataSource = SourceAudit;
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
		readBlock(block);
	}
}

/**
 * Wait for a read request to be made
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
 * Trigger the loading thread to read a block of data
 */
void DataLoad::triggerRead(unsigned int blockSize)
{
	unique_lock<mutex> lck(m_mutex);
	m_readRequest = blockSize;
	m_cv.notify_all();
}

/**
 * Read a block of readings from the storage service
 *
 * @param blockSize	The number of readings to fetch
 */
void DataLoad::readBlock(unsigned int blockSize)
{
ReadingSet *readings = NULL;

	do
	{
		try
		{
			switch (m_dataSource)
			{
				case SourceReadings:
					Logger::getLogger()->debug("Fetch %d readings from %d", blockSize, m_lastFetched + 1);
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
			Logger::getLogger()->error("North Service '%s', failed to fetch data, Exception '%s'", m_name.c_str(), e->what());
		}
	       	catch (exception& e)
		{
			Logger::getLogger()->error("North Service '%s', failed to fetch data, Exception '%s'", m_name.c_str(), e.what());
		}
		if (readings && readings->getCount())
		{
			m_lastFetched = readings->getLastId();
			bufferReadings(readings);
			return;
		}
		else
		{
			Logger::getLogger()->debug("No readings available");
		}
		if (!m_shutdown)
		{	
			// TODO improve this
			this_thread::sleep_for(chrono::milliseconds(250));
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

	columns.push_back(new Returns("log"));
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
			return (unsigned long)theVal->getInteger();
		}
	}
	// Free result set
	delete lastObjectId;

	return 0;
}

/**
 * Buffer a block of readings
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
		triggerRead(100);	// TODO Improve this
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
	triggerRead(100);	// TODO Improve this
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
	const Condition condition(Equals);
	Where where("id", condition, to_string(m_streamId));
	InsertValues lastId;

	lastId.push_back(InsertValue("last_object", (long)id));
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
	if (readingSet->getCount() == 0)	// Special case when all filtered out
	{
		load->updateLastSentId(load->m_lastFetched);
	}

	unique_lock<mutex> lck(load->m_qMutex);
	load->m_queue.push_back(readingSet);
	load->m_fetchCV.notify_all();
}

/**
 * Update the sent statistics
 *
 * @param increment	Increment of the number of readings sent
 */
void DataLoad::updateStatistics(uint32_t increment)
{
	updateStatistic(m_name, m_name + " Readings Sent", increment);
	updateStatistic("Readings Sent", "Readings Sent North", increment);
}

/**
 * Update a particular statstatistic
 *
 * @param key		The statistic key
 * @param description	The statistic description
 * @param increment	Increment of the number of readings sent
 */
void DataLoad::updateStatistic(const string& key, const string& description, uint32_t increment)
{
	const Condition conditionStat(Equals);
	Where wLastStat("key", conditionStat, key);

	// Prepare value = value + inc
	ExpressionValues updateValue;
	updateValue.push_back(Expression("value", "+", (int)increment));

	// Perform UPDATE fledge.statistics SET value = value + x WHERE key = 'name'
	int row_affected = m_storage->updateTable("statistics", updateValue, wLastStat);

	if (row_affected == -1)
	{
		// The required row is not in the statistics table yet
		// this situation happens only at the initial setup
		// adding the required row.

		Logger::getLogger()->info("Adding a new row into the statistics as it is not present yet, key -%s- description -%s-",
				key.c_str(), description.c_str()); 
		InsertValues values;
		values.push_back(InsertValue("key",         key));
		values.push_back(InsertValue("description", description));
		values.push_back(InsertValue("value",       (int)increment));
		string table = "statistics";

		if (m_storage->insertTable(table, values) != 1)
		{
			Logger::getLogger()->error("Failed to insert a new row into the %s", table.c_str());
		}
		else
		{
			Logger::getLogger()->info("New row added into the %s, key -%s- description -%s-",
				table.c_str(), key.c_str(), description.c_str());

                }
	}
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
			if (m_pipeline)
			{
				if (newPipeline == "" ||
				    m_pipeline->hasChanged(newPipeline) == false)
				{
					Logger::getLogger()->info("Ingest::configChange(): "
								  "filter pipeline is not set or "
								  "it hasn't changed");
					return;
				}
				/* The new filter pipeline is different to what we have already running
				 * So remove the current pipeline and recreate.
			 	 */
				Logger::getLogger()->info("Ingest::configChange(): "
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
		Logger::getLogger()->info("Ingest::configChange(): change to config of some filter(s)");
		lock_guard<mutex> guard(m_pipelineMutex);
		if (m_pipeline)
		{
			m_pipeline->configChange(category, newConfig);
		}
	}
}
