/*
 * Fledge SQLite storage plugin database control block
 *
 * Copyright (c) 2024 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */

#include <dbcb.h>
#include <databasehandler.h>

/**
 * Constructor for the database control block
 *
 * @param op	The operation that is being executed
 * @param table	The name of the table that is being updated
 */
DBCB::DBCB(DBCB::Operation op, const std::string& table) : m_op(op), m_table(table),
							   m_status(Created), m_handler(NULL)
{
	m_logger = Logger::getLogger();
}

/**
 * Destructor for the database control block
 */
DBCB::~DBCB()
{
}

/**
 * Queue the database control block to the database handler
 *
 * @param handler	The database handler that will handle this request
 * @return bool		Return true if the request was queued succesfully
 */
bool DBCB::queue(DatabaseHandler *handler)
{
	m_status = Queued;
	m_handler = handler;
	if (!handler->queueRequest(this))
	{
		m_status = FailedToQueue;
		return false;
	}
	return true;
}

/**
 * AppendDBCB constructor for the database control block used to insert
 * readings into the storage plugin.
 *
 * @param table		The name of the table we are inserting into
 */
AppendDBCB::AppendDBCB(const std::string& table) : DBCB(DBCB::OpInsert, table)
{
}

/**
 * Destructor for the append database control block
 */
AppendDBCB::~AppendDBCB()
{
}

/**
 * Append reading to the list of readings waiting to be written to
 * the table.
 *
 * @param reading	The reading to insert
 */
void AppendDBCB::addReading(Reading *reading)
{
	m_readings.push_back(reading);
}

/**
 * Execute an insert into the SQLite storage plugin
 *
 * @return bool		Return true if the append operation succeeded
 */
bool AppendDBCB::execute()
{
	return false;
}

/**
 * Constructor for the Purge database control block
 *
 * @param table	The table to be purged
 */
PurgeDBCB::PurgeDBCB(const std::string& table) : DBCB(DBCB::OpDelete, table)
{
}

/**
 * Destructor for the Purge database control block
 */
PurgeDBCB::~PurgeDBCB()
{
}

/**
 * Set the reading ID limit for the purge operation
 *
 * @param readingId	The highest value reading ID to be purged
 */
void PurgeDBCB::purge(unsigned long readingId)
{
	m_readingId = readingId;
}

/**
 * Execute the purge operaton on the database table
 *
 * @return bool		Return true if the append operation succeeded
 */
bool PurgeDBCB::execute()
{
	return false;
}
