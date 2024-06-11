#ifndef _CHECK_UPDATES_H
#define _CHECK_UPDATES_H

/*
 * Fledge Check Updates
 *
 * Copyright (c) 2024 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Devki Nandan Ghildiyal
 */

#include <process.h>

#define LOG_NAME "check_updates"

/**
 * CheckUpdates class
 */

class CheckUpdates : public FledgeProcess
{
	public:
		CheckUpdates(int argc, char** argv);
		~CheckUpdates();
		void run();

	private:
		Logger *m_logger;
		ManagementClient *m_mgtClient;

		void raiseAlerts();
		std::string getPackageManager();
		std::vector<std::string> getUpgradablePackageList();
		void processEnd();
};
#endif
