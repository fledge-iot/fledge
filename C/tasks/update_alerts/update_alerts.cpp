/*
 * Fledge Update Alerts
 *
 * Copyright (c) 2024 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Devki Nandan Ghildiyal
 */

#include <update_alerts.h>
#include <logger.h>

#include <cstdlib>
#include <thread>
#include <csignal>
#include <fstream>

using namespace std;

volatile std::sig_atomic_t signalReceived = 0;


static void signalHandler(int signal)
{
	signalReceived = signal;
}


/**
 * Constructor for UpdateAlerts
 */
UpdateAlerts::UpdateAlerts(int argc, char** argv) : FledgeProcess(argc, argv)
{
	std::string paramName;
	paramName = getName();
	m_logger = new Logger(paramName);
	m_logger->info("UpdateAlerts starting - parameters name :%s:", paramName.c_str() );
	m_mgtClient = this->getManagementClient();

}

/**
 * Destructor for UpdateAlerts
 */
UpdateAlerts::~UpdateAlerts()
{
}

/**
 * UpdateAlerts run method, called by the base class to start the process and do the actual work.
 */
void UpdateAlerts::run()
{
	// We handle these signals, add more if needed
	std::signal(SIGINT,  signalHandler);
	std::signal(SIGSTOP, signalHandler);
	std::signal(SIGTERM, signalHandler);


	if (!m_dryRun)
	{
		updateAlets();
	}
	processEnd();
}

/**
 * Execute the updateAlets, create an alert for all the packages for which update is available
 */
void UpdateAlerts::updateAlets()
{
	m_logger->info("updateAlets running");
	try
	{
		for (auto m: getUpgradablePackageList())
		{
			ostringstream   payload;
			payload << "\"key\":\"" << m  << "\","
						<< "\"message\":\"A new update is available for " << m << "\","
						<< "\"urgency\":\"normal\"";
			
			if (!m_mgtClient->raiseAlert(payload.str()))
			{
				m_logger->error("Failed to raise alert");
			}

		}

	}
	catch (...)
	{
		std::exception_ptr p = std::current_exception();
		string errorInfo = (p ? p.__cxa_exception_type()->name() : "null");

		m_logger->error("Failed to raise alert : %s",errorInfo.c_str());
	}
}

/**
 * Logs process end message
 */

void UpdateAlerts::processEnd()
{
	m_logger->info("UpateAlerts completed");
}

/**
 * Fetch package manager name 
 */

std::string UpdateAlerts::getPackageManager() 
{
	std::string command = "command -v yum || command -v apt-get";
	std::string result = "";
	char buffer[128];
	
	// Open pipe to file
	FILE* pipe = popen(command.c_str(), "r");
	if (!pipe)
	{
		m_logger->debug("getPackageManager: popen call failed");
		return "";
	}
	// read till end of process:
	while (!feof(pipe))
	{
		if (fgets(buffer, 128, pipe) != NULL)
			result += buffer;
	}

	pclose(pipe);

	if (result.find("apt") != std::string::npos)
		return "apt";
	if (result.find("yum") != std::string::npos)
		return "yum";

	m_logger->debug("Unspported environment");
	return "";
}

/**
 * Fetch a list of all the package name for which upgrade is available
 */
std::vector<std::string> UpdateAlerts::getUpgradablePackageList() 
{
	std::string packageManager = getPackageManager();
	std::vector<std::string> packageList;
	if(!packageManager.empty())
	{
		std::string packageListFile = "/tmp/fledge.upgrade.list";
		std::string command = "apt list --upgradeable | grep fledge | cut -d'/' -f1 > " + packageListFile;
		if (packageManager.find("yum") != std::string::npos)
		{
			command = "yum check-update | grep fledge | cut -d'/' -f1 > " + packageListFile;
			system(command.c_str());
			std::ifstream file(packageListFile);
			if(!file.is_open())
			{
				m_logger->debug("Couldnot read package list");
				return packageList;
			}
			std::string packageName; 
			while (std::getline(file, packageName))
			{
				packageList.emplace_back(packageName);
			}
		}
	}

	return packageList;
}