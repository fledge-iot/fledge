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

#include <stdarg.h>     /* va_list, va_start, va_arg, va_end */
#include <stdlib.h>
#include <thread>
#include <csignal>

using namespace std;

volatile std::sig_atomic_t signalReceived = 0;

static const string defaultConfig = QUOTE({
	"retainStatsHistory": {
		"description": "This is the measure of how long to retain statistics history data for and should be measured in days.",
		"type": "integer",
		"default": "7",
		"displayName": "Retain Stats History Data (In Days)",
		"order": "1",
		"minimum": "1"
	},
	"retainAuditLog" : {
		"description": "This is the measure of how long to retain audit trail information for and should be measured in days.",
		"type": "integer",
		"default": "30",
		"displayName": "Retain Audit Trail Data (In Days)",
		"order": "2",
		"minimum": "1"
	},
	"retainTaskHistory" : {
		"description": "This is the measure of how long to retain task history information for and should be measured in days.",
		"type": "integer",
		"default": "30",
		"displayName": "Retain Task History Data (In Days)",
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
	m_logger = new Logger(LOG_NAME);

	//# FIXME_I
	m_logger->setMinLevel("debug");

	//# FIXME_I
	m_logger->info("xxx2 PurgeSystem starting - parameters name :%s:", getName().c_str() );
}

PurgeSystem::~PurgeSystem()
{
	//# FIXME_I
	m_logger->setMinLevel("debug");

	;
}

void PurgeSystem::purgeExecution()
{
	//# FIXME_I
	m_logger->info("xxx2 PurgeSystem execution");
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

	ConfigCategory configuration = configurationHandling(defaultConfig);

	m_logger->debug("xxx2 BRK 1");

	try {
		m_retainStatsHistory = strtoul(configuration.getValue("retainStatsHistory").c_str(), NULL, 10);
		m_retainAuditLog     = strtoul(configuration.getValue("retainAuditLog").c_str(), NULL, 10);
		m_retainTaskHistory  = strtoul(configuration.getValue("retainTaskHistory").c_str(), NULL, 10);

	} catch (const std::exception &e) {
		raiseError ("impossible to retrieve the configuration :%s:", e.what() );
	}

	m_logger->debug("xxx2 BRK 2");

	m_logger->info("xxx2 configuration retainStatsHistory :%d: retainAuditLog :%d: retainTaskHistory :%d:"
				   ,m_retainStatsHistory
				   ,m_retainAuditLog
				   ,m_retainTaskHistory);

	purgeExecution();
	processEnd();
}

/**
 */
void PurgeSystem::processEnd() const
{
	//# FIXME_I
	m_logger->setMinLevel("debug");
	m_logger->info("xxx2  PurgeSystem completed");
	m_logger->setMinLevel("warning");
}

/**
 */
ConfigCategory PurgeSystem::configurationHandling(const std::string& config)
{
	// retrieves the configuration using the value of the --name parameter
	// (received in the command line) as the key
	string categoryName(this->getName());

	//# FIXME_I
	m_logger->setMinLevel("debug");
	m_logger->debug("xxx2 %s - categoryName :%s:", __FUNCTION__, categoryName.c_str());
	m_logger->setMinLevel("warning");

	ConfigCategory configuration;
	ConfigCategory advancedConfiguration;

	// Create category, with "default" values only
	DefaultConfigCategory category(categoryName, config);
	category.setDescription(CONFIG_CATEGORY_DESCRIPTION);

	// Create/Update category name (we pass keep_original_items=true)
	if (! this->getManagementClient()->addCategory(category, true))
	{
		raiseError ("Failure creating/updating configuration key :%s: ", categoryName.c_str() );
	}

	return ConfigCategory(configuration);
}