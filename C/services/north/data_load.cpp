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
	m_readRequest(0), m_dataSource(SourceReadings)
{
	m_thread = new thread(threadMain, this);
}

/**
 * DataLoad destructor
 *
 * Shutdown and wait for the loading thread
 */
DataLoad::~DataLoad()
{
	// Request the loading thread to shutdown and wait for it
	m_shutdown = true;
	m_cv.notify_all();
	m_fetchCV.notify_all();
	m_thread->join();
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
	delete m_thread;
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
	return m_readRequest;
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
					readings = m_storage->readingFetch(m_lastFetched + 1, blockSize);
					break;
				case SourceStatistics:
					readings = fetchStatistics(blockSize);
					break;
				case SourceAudit:
					readings = fetchAudit(blockSize);
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
			bufferReadings(readings);
			return;
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
long DataLoad::getLastSentId()
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
			return theVal->getInteger();
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
	unique_lock<mutex> lck(m_mutex);
	m_queue.push_back(readings);
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
	return streamId;
}

/**
 * Update the last sent ID for our stream
 */
void DataLoad::updateLastSentId(long id)
{
	const Condition condition(Equals);
	Where where("id", condition, to_string(m_streamId));
	InsertValues lastId;

	lastId.push_back(InsertValue("last_object", (long)id));
	m_storage->updateTable("streams", lastId, where);
}

