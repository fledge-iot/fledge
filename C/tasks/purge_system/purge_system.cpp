/*
 * Fledge Statistics History
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
 *
 */
void PurgeSystem::raiseError(const char *reason, ...)
{
	//By default Syslog is limited to a message size of 1024 bytes
	char buffer[1024];

	va_list ap;
	va_start(ap, reason);
	vsnprintf(buffer, sizeof(buffer), reason, ap);
	va_end(ap);

	m_logger->error("%PI Web API plugin raising error: %s", buffer);
	throw runtime_error(buffer);
}

PurgeSystem::PurgeSystem(int argc, char** argv) : FledgeProcess(argc, argv)
{
	string paramName;

	paramName = getName();

	m_logger = new Logger(paramName);
	m_logger->info("xxx2 PurgeSystem starting - parameters name :%s:", paramName.c_str() );

	m_retainStatsHistory = 0;
	m_retainAuditLog = 0;
	m_retainTaskHistory = 0;

	m_storage = this->getStorageClient();
}

PurgeSystem::~PurgeSystem()
= default;

/**
 * PurgeSystem run method, called by the base class
 * to start the process and do the actual work.
 */
void PurgeSystem::run()
{
	//# FIXME_I
	m_logger->setMinLevel("debug");

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

	m_logger->info("xxx2 configuration retainStatsHistory :%d: retainAuditLog :%d: retainTaskHistory :%d:"
				   ,m_retainStatsHistory
				   ,m_retainAuditLog
				   ,m_retainTaskHistory);

	purgeExecution();
	processEnd();

	//# FIXME_I
	m_logger->setMinLevel("debug");
}

/**
 */
ConfigCategory PurgeSystem::configurationHandling(const std::string& config)
{
	// retrieves the configuration using the value of the --name parameter
	// (received in the command line) as the key
	string categoryName(this->getName());

	ConfigCategory configuration;

	//# FIXME_I
	m_logger->debug("xxx2 %s - categoryName :%s:", __FUNCTION__, categoryName.c_str());

	// Create category, with "default" values only
	DefaultConfigCategory defaultConfig(categoryName, config);
	defaultConfig.setDescription(CONFIG_CATEGORY_DESCRIPTION);

	// Create/Update category name (we pass keep_original_items=true)
	if (! this->getManagementClient()->addCategory(defaultConfig, true))
	{
		raiseError ("Failure creating/updating configuration key :%s: ", categoryName.c_str() );
	}

	// Get the category with values and defaults
	configuration = this->getManagementClient()->getCategory(categoryName);

	return ConfigCategory(configuration);
}

void PurgeSystem::purgeExecution()
{
	//# FIXME_I
	m_logger->info("xxx2 PurgeSystem running");

	purgeTable("statistics_history", "history_ts", m_retainStatsHistory);

	//purgeTable("tasks",              m_retainAuditLog);
	///purgeTable("log",                m_retainTaskHistory);

}

void PurgeSystem::purgeTable(const std::string& tableName, const std::string& fieldName, int retentionDays)
{
	int affected;
	string conditionValue;

	//# FIXME_I
	Logger::getLogger()->setMinLevel("debug");

	//const Condition _condition(LessThan);
	const Condition conditionExpr(Older);

	// FIXME_I:
	//conditionDays = "datetime('now','-" + to_string(retentionDays) + " day')";
	//conditionValue = to_string (retentionDays * 60 * 60 * 24); // the days should be expressed in seconds
	conditionValue = to_string (retentionDays); // the days should be expressed in seconds
	m_logger->debug("xxx2 %s - purging :%s: retention days :%d: conditionValue :%s:", __FUNCTION__, tableName.c_str(), retentionDays, conditionValue.c_str() );
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

	m_logger->debug("xxx2 %s - %s rows purged :%d:", __FUNCTION__, tableName.c_str(), affected);
}

/**
 */
void PurgeSystem::processEnd() const
{
	//# FIXME_I
	m_logger->info("xxx2 PurgeSystem completed");
}

