/*
 * Fledge Purge System - purge tables in the fledge database
 *
 * Copyright (c) 2021 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Stefano Simonelli
 */

#include <purge_system.h>
#include <logger.h>

#include <cstdarg>     /* va_list, va_start, va_arg, va_end */
#include <cstdlib>
#include <thread>
#include <csignal>

using namespace std;

volatile std::sig_atomic_t signalReceived = 0;

static const string DEFAULT_CONFIG = QUOTE({
	"retainStatsHistory": {
		"description": "The number of days for which full granularity statistics history is maintained.",
		"type": "integer",
		"default": "7",
		"displayName": "Statistics Retention",
		"order": "1",
		"minimum": "1"
	},
	"retainAuditLog" : {
		"description": "The number of days for which audit trail data is retained",
		"type": "integer",
		"default": "30",
		"displayName": "Audit Retention",
		"order": "2",
		"minimum": "1"
	},
	"retainTaskHistory" : {
		"description": "The number of days for which task history is retained",
		"type": "integer",
		"default": "30",
		"displayName": "Task Retention",
		"order": "3",
		"minimum": "1"
	}
});

static void signalHandler(int signal)
{
	signalReceived = signal;
}

/**
 * Error handler - logs the error and raises the exception
 */
void PurgeSystem::raiseError(const char *reason, ...)
{
	//By default Syslog is limited to a message size of 1024 bytes
	char buffer[1024];

	va_list ap;
	va_start(ap, reason);
	vsnprintf(buffer, sizeof(buffer), reason, ap);
	va_end(ap);

	m_logger->error("PurgeSystem raising error: %s", buffer);
	throw runtime_error(buffer);
}

/**
 * Constructor for Purge system
 */
PurgeSystem::PurgeSystem(int argc, char** argv) : FledgeProcess(argc, argv)
{
	string paramName;

	paramName = getName();

	m_logger = new Logger(paramName);
	m_logger->info("PurgeSystem starting - parameters name :%s:", paramName.c_str() );

	m_retainStatsHistory = 0;
	m_retainAuditLog = 0;
	m_retainTaskHistory = 0;

	m_storage = this->getStorageClient();
}

/**
 *
 */
PurgeSystem::~PurgeSystem()
{
}

/**
 * PurgeSystem run method, called by the base class
 * to start the process and do the actual work.
 */
void PurgeSystem::run()
{
	// We handle these signals, add more if needed
	std::signal(SIGINT,  signalHandler);
	std::signal(SIGSTOP, signalHandler);
	std::signal(SIGTERM, signalHandler);

	ConfigCategory configuration = configurationHandling(DEFAULT_CONFIG);

	try {
		m_retainStatsHistory = strtoul(configuration.getValue("retainStatsHistory").c_str(), nullptr, 10);
		m_retainAuditLog     = strtoul(configuration.getValue("retainAuditLog").c_str(), nullptr, 10);
		m_retainTaskHistory  = strtoul(configuration.getValue("retainTaskHistory").c_str(), nullptr, 10);

	} catch (const std::exception &e) {
		raiseError ("impossible to retrieve the configuration :%s:", e.what() );
	}

	m_logger->info("configuration retainStatsHistory :%d: retainAuditLog :%d: retainTaskHistory :%d:"
				   ,m_retainStatsHistory
				   ,m_retainAuditLog
				   ,m_retainTaskHistory);

	purgeExecution();
	processEnd();
}

/**
 * Retrieves and store the configuration
 *
 * @param   config  Default configuration
 */
ConfigCategory PurgeSystem::configurationHandling(const std::string& config)
{
	// retrieves the configuration using the value of the --name parameter
	// (received in the command line) as the key
	string categoryName(this->getName());

	ConfigCategory configuration;

	ManagementClient *client = this->getManagementClient();

	m_logger->debug("%s - categoryName :%s:", __FUNCTION__, categoryName.c_str());

	// Create category, with "default" values only
	DefaultConfigCategory defaultConfig(categoryName, config);
	defaultConfig.setDescription(CONFIG_CATEGORY_DESCRIPTION);
	defaultConfig.setDisplayName(CONFIG_CATEGORY_DISPLAY_NAME);

	// Create/Update category name (we pass keep_original_items=true)
	if (! client->addCategory(defaultConfig, true))
	{
		raiseError ("Failure creating/updating configuration key :%s: ", categoryName.c_str() );
	}

	// Purge system category as child of Utilities
	{
		vector<string> children;
		children.push_back(categoryName);
		ConfigCategories categories = client->getCategories();
		try {
			bool found = false;
			for (unsigned int idx = 0; idx < categories.length(); idx++)
			{
				if (categories[idx]->getName().compare(UTILITIES_CATEGORY) == 0)
				{
					client->addChildCategories(UTILITIES_CATEGORY, children);
					found = true;
				}
			}
			if (!found)
			{
				raiseError("adding %s as a child of %s", categoryName.c_str(), UTILITIES_CATEGORY);
			}
		} catch (...) {
			std::exception_ptr p = std::current_exception();
			string errorInfo = (p ? p.__cxa_exception_type()->name() : "null");

			raiseError("adding %s as a child of %s - %s", categoryName.c_str(), UTILITIES_CATEGORY, errorInfo.c_str());
		}
	}

	// Get the category with values and defaults
	configuration = client->getCategory(categoryName);

	return ConfigCategory(configuration);
}

/**
 * Execute the purge, store information in an historicization table and delete teh information
 * the tables currently handled are:
 *
 *   - fledge.statistics_history
 *   - fledge.tasks
 *   - fledge.log
 */
void PurgeSystem::purgeExecution()
{
	string tableName;

	m_logger->info("PurgeSystem running");

	tableName = "statistics_history";
	try {
		historicizeData(m_retainStatsHistory);
		purgeTable(tableName, "history_ts", m_retainStatsHistory);

	} catch (const std::exception &e) {

		raiseError ("Failure historicizing and purging table :%s: :%s:",tableName.c_str(),  e.what() );
	}

	purgeTable("tasks", "start_time", m_retainTaskHistory);
	purgeTable("log", "ts", m_retainAuditLog);
}

/**
 * Store statistics_history details information in a historicization table
 *
 * @param   retentionDays  Number of days to retain
 */
void PurgeSystem::historicizeData(unsigned long retentionDays)
{
	string tableSource;
	string fieldName;
	string tableDest;
	ResultSet *data;

	tableSource="statistics_history";
	fieldName="history_ts";
	tableDest="statistics_history_daily";

	m_logger->debug("%s - historicizing :%s: retention days :%d: ", __FUNCTION__, tableSource.c_str(), retentionDays);

	data = extractData(tableSource, fieldName, retentionDays);

	if (data->rowCount()) {

		try {
			storeData(tableDest, data);

		} catch (const std::exception &e) {

			;
		}
	}

	delete data;
}

/**
 * Retrieve grouped information to historicize
 *
 * @param   tableName      Name of the table from which the records should be extracted
 * @param   fieldName      Timestamp on which the where condition should be based on
 * @param   retentionDays  Number of days to retain
 *
 * @return  Retrieved recordset
 */
ResultSet *PurgeSystem::extractData(const std::string& tableName, const std::string& fieldName, unsigned long retentionDays)
{
	ResultSet *data;
	string conditionValue;

	data = nullptr;

	const Condition conditionExpr(Older);
	conditionValue = to_string (retentionDays * 60 * 60 * 24); // the days should be expressed in seconds
	//conditionValue = to_string (retentionDays);

	Where *_where     = new Where(fieldName, conditionExpr, conditionValue);
	Query _query(_where);

	// Alias handling is ignored because of the presence of the group by
	//	vector<Returns *> _returns {};
	//	_returns.push_back(new Returns("date(history_ts)", "date") );
	//	_returns.push_back(new Returns("key") );
	//	_query.returns(_returns);

	Aggregate *_aggregate = new Aggregate("sum", "value");
	_query.aggregate(_aggregate);

	_query.group("date(history_ts), key");

	try
	{
		data = m_storage->queryTable(tableName, _query);
		if (data == nullptr)
		{
			raiseError ("Failure extracting data from the table :%s: ", tableName.c_str() );
		}

	} catch (const std::exception &e) {

		raiseError ("Failure extracting data :%s:", e.what() );
	}

	m_logger->debug("%s - %s rows extracted :%d:", __FUNCTION__, tableName.c_str(), data->rowCount() );

	return (data);
}

/**
 * Store the content of the provided recordset in the given table
 *
 * @param   tableDest  Name of the table in which the recordset should be stored
 * @param   data       recordset to store on the table tableDest
 */
void PurgeSystem::storeData(const std::string& tableDest, ResultSet *data)
{
	long   fieldYear;
	string fieldDate;
	string fieldKey;
	long   fieldValue = 0;

	int affected = 0;

	bool retrieved;

	try
	{
		m_logger->debug("%s - storing in :%s: rows :%d:", __FUNCTION__, tableDest.c_str(), data->rowCount() );

		ResultSet::RowIterator item = data->firstRow();
		do
		{
			ResultSet::Row* row = *item;

			if (row)
			{
				// SQLite and PostgreSQL plugins behave differently, it initially tries the code for SQLite and in case
				// of an error it executes the PostgreSQL one
				try {
					fieldDate = row->getColumn("date(history_ts)")->getString();
					retrieved = true;

				} catch (...) {
					retrieved = false;
				}
				if (! retrieved)
				{
					fieldDate = row->getColumn("date")->getString();
				}

				fieldYear = strtol(fieldDate.substr(0, 4).c_str(), nullptr, 10);
				fieldKey = row->getColumn("key")->getString();

				// SQLite and PostgreSQL plugins behave differently, it initially tries the code for SQLite and in case
				// of an error it executes the PostgreSQL one
				try {
					fieldValue = row->getColumn("sum_value")->getInteger();
					retrieved = true;
				} catch (...) {
					retrieved = false;
				}
				if (! retrieved)
				{
					fieldValue = strtol(row->getColumn("sum_value")->getString(), nullptr, 10);
				}

				InsertValues values;
				values.push_back(InsertValue("year", fieldYear) );
				values.push_back(InsertValue("day", fieldDate) );
				values.push_back(InsertValue("key", fieldKey) );
				values.push_back(InsertValue("value", fieldValue) );

				m_logger->debug("%s - :%s: inserting :%ld: :%s: :%s: :%ld:  ", __FUNCTION__, tableDest.c_str()
					, fieldYear
					, fieldDate.c_str()
					, fieldKey.c_str()
					, fieldValue);

				affected = m_storage->insertTable(tableDest, values);
				if (affected == -1)
				{
					raiseError ("Failure inserting rows into :%s: ", tableDest.c_str() );
				}
			}

		} while (!data->isLastRow(item++));

	} catch (const std::exception &e) {

		raiseError ("Failure inserting rows into :%s: error :%s: ", tableDest.c_str(), e.what() );
	}
}

/**
 * Purge the content of the given table from the information older than a provided number of days
 *
 * @param   tableName      Name of the table to purge
 * @param   fieldName      Timestamp on which the where condition should be based on
 * @param   retentionDays  Number of days to retain
 */
void PurgeSystem::purgeTable(const std::string& tableName, const std::string& fieldName, unsigned long retentionDays)
{
	int affected;
	string conditionValue;
	affected = 0;

	const Condition conditionExpr(Older);

	conditionValue = to_string (retentionDays * 60 * 60 * 24); // the days should be expressed in seconds
	//conditionValue = to_string (retentionDays);

	m_logger->debug("%s - purging :%s: retention days :%d: conditionValue :%s:", __FUNCTION__, tableName.c_str(), retentionDays, conditionValue.c_str() );

	Where *_where = new Where(fieldName, conditionExpr, conditionValue);
	Query _query(_where);
	try
	{
		affected = m_storage->deleteTable(tableName, _query);
		if (affected == -1)
		{
			raiseError ("Failure purging the table :%s: ", tableName.c_str() );
		}

	} catch (const std::exception &e) {

		raiseError ("Failure purging the table :%s: ", tableName.c_str() );
	}

	m_logger->debug("%s - %s rows purged :%d:", __FUNCTION__, tableName.c_str(), affected);
}

/**
 * Terminate the operation
 *
 */
void PurgeSystem::processEnd() const
{
	m_logger->info("PurgeSystem completed");
}
