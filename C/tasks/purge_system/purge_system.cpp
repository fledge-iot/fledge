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
	string paramName;

	paramName = getName();

	m_logger = new Logger(paramName);
	m_logger->info("xxx2 PurgeSystem starting - parameters name :%s:", paramName.c_str() );

	m_retainStatsHistory = 0;
	m_retainAuditLog = 0;
	m_retainTaskHistory = 0;
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
	m_logger->info("xxx2 PurgeSystem execution");
}

/**
 */
void PurgeSystem::processEnd() const
{
	//# FIXME_I
	m_logger->info("xxx2 PurgeSystem completed");
}

