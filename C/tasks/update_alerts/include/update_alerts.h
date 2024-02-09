#ifndef _UPDATE_ALERTS_H
#define _UPDATE_ALERTS_H

/*
 * Fledge Update Alerts
 *
 * Copyright (c) 2024 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Devki Nandan Ghildiyal
 */

#include <process.h>

#define LOG_NAME "update_alerts"

/**
 * UpdateAlerts class
 */

class UpdateAlerts : public FledgeProcess
{
	public:
		UpdateAlerts(int argc, char** argv);
		~UpdateAlerts();
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
