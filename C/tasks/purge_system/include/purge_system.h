#ifndef _PURGE_SYSTEM_H
#define _PURGE_SYSTEM_H

/*
 * Fledge Statistics History
 *
 * Copyright (c) 2021 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Stefano Simonelli
 */

#include <process.h>

#define TO_STRING(...) DEFER(TO_STRING_)(__VA_ARGS__)
#define DEFER(x) x
#define TO_STRING_(...) #__VA_ARGS__
#define QUOTE(...) TO_STRING(__VA_ARGS__)

#define LOG_NAME                     "purge_system"
#define CONFIG_CATEGORY_DESCRIPTION  "Configuration of the Purge System"
#define CONFIG_CATEGORY_DISPLAY_NAME "Purge System"


#define UTILITIES_CATEGORY	  "Utilities"


class PurgeSystem : public FledgeProcess
{
	public:
		PurgeSystem(int argc, char** argv);
		~PurgeSystem();

		void     run();

	private:
		Logger        *m_logger;
		StorageClient *m_storage;
		unsigned long  m_retainStatsHistory;
		unsigned long  m_retainAuditLog;
		unsigned long  m_retainTaskHistory;

	private:
		void           raiseError(const char *reason, ...);
		void           purgeExecution();
		void           purgeTable(const std::string& tableName, const std::string& fieldName, unsigned long retentionDays);
		void           historicizeData(unsigned long retentionDays);
		ResultSet     *extractData(const std::string& tableName, const std::string& fieldName, unsigned long retentionDays);
		void           storeData(const std::string& tableDest, ResultSet *data);
		void           processEnd() const;
		ConfigCategory configurationHandling(const std::string& config);
};

#endif
