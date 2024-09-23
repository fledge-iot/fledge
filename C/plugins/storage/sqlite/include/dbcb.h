/*
 * Fledge database control block
 *
 * Copyright (c) 2024 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#ifndef _DBCB_H
#define _DBCB_H

#include <logger.h>
#include <string>
#include <vector>

class DatabaseHandler;
class Reading;

/**
 * A databse control block. This is used to track requests to the
 * threads that perform the insert, updates and deletes on the readings
 * databases uses the per databse threads
 */
class DBCB {
	public:
		enum Operation {
			OpInsert, OpUpdate, OpDelete
		};
		enum Status {
			Created, Queued, InProgress, Complete, Failed, FailedToQueue
		};
		DBCB(DBCB::Operation op, const std::string& table);
		virtual ~DBCB();
		Status		status()
				{
					return m_status;
				};
		bool		queue(DatabaseHandler *handler);
		virtual bool	execute() = 0;
	protected:
		Operation	m_op;
		std::string	m_table;
		Logger		*m_logger;
		Status		m_status;
		DatabaseHandler	*m_handler;
};

/**
 * The database control block used to append readings to the
 * SQLite readings table
 */
class AppendDBCB : public DBCB {
	public:
		AppendDBCB(const std::string& table);
		~AppendDBCB();
		bool		execute();
		void		addReading(Reading *);
	private:
		std::vector<Reading *>
				m_readings;
};

/**
 * The database control block used to purge readings from the
 * SQLite readings table
 */
class PurgeDBCB : public DBCB {
	public:
		PurgeDBCB(const std::string& table);
		~PurgeDBCB();
		bool		execute();
		void		purge(unsigned long readingId);
	private:
		unsigned long	m_readingId;
};

#endif
