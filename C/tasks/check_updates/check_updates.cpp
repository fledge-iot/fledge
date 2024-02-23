/*
 * Fledge Check Updates
 *
 * Copyright (c) 2024 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Devki Nandan Ghildiyal
 */

#include <check_updates.h>
#include <logger.h>

#include <cstdlib>
#include <thread>
#include <csignal>
#include <fstream>
#include <errno.h>

using namespace std;

volatile std::sig_atomic_t signalReceived = 0;
std::string packageListFile = "/tmp/fledge.upgrade.list";

static void signalHandler(int signal)
{
	signalReceived = signal;
}


/**
 * Constructor for CheckUpdates
 */
CheckUpdates::CheckUpdates(int argc, char** argv) : FledgeProcess(argc, argv)
{
	std::string paramName;
	paramName = getName();
	m_logger = new Logger(paramName);
	m_logger->info("CheckUpdates starting - parameters name :%s:", paramName.c_str() );
	m_mgtClient = this->getManagementClient();

}

/**
 * Destructor for CheckUpdates
 */
CheckUpdates::~CheckUpdates()
{
}

/**
 * CheckUpdates run method, called by the base class to start the process and do the actual work.
 */
void CheckUpdates::run()
{
	// We handle these signals, add more if needed
	std::signal(SIGINT,  signalHandler);
	std::signal(SIGSTOP, signalHandler);
	std::signal(SIGTERM, signalHandler);


	if (!m_dryRun)
	{
		raiseAlerts();
	}
	processEnd();
}

/**
 * Execute the raiseAlerts, create an alert for all the packages for which update is available
 */
void CheckUpdates::raiseAlerts()
{
	m_logger->info("raiseAlerts running");
	try
	{
		for (auto key: getUpgradablePackageList())
		{
			std::string message = "A newer version of " + key + " is available for upgrade";
			std::string urgency = "normal";
			if (!m_mgtClient->raiseAlert(key,message,urgency))
			{
				m_logger->error("Failed to raise an alert for key=%s,message=%s,urgency=%s", key.c_str(), message.c_str(), urgency.c_str());
			}
		}
		std::string command = "sudo rm -f " + packageListFile;
		system(command.c_str());

	}
	catch (...)
	{
		try
		{
			std::exception_ptr p = std::current_exception();
			std::rethrow_exception(p);
		}
		catch(const std::exception& e)
		{
			m_logger->error("Failed to raise alert : %s", e.what());
		}

	}
}

/**
 * Logs process end message
 */

void CheckUpdates::processEnd()
{
	m_logger->info("raiseAlerts completed");
}

/**
 * Fetch package manager name 
 */

std::string CheckUpdates::getPackageManager() 
{
	std::string command = "command -v yum || command -v apt-get";
	std::string result = "";
	char buffer[128];
	
	// Open pipe to file
	FILE* pipe = popen(command.c_str(), "r");
	if (!pipe)
	{
		m_logger->error("getPackageManager: popen call failed : %s",strerror(errno));
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

	m_logger->warn("Unspported environment %s", result.c_str() );
	return "";
}

/**
 * Fetch a list of all the package name for which upgrade is available
 */
std::vector<std::string> CheckUpdates::getUpgradablePackageList() 
{
	std::string packageManager = getPackageManager();
	std::vector<std::string> packageList;
	if(!packageManager.empty())
	{
		std::string command = "sudo apt update && sudo apt list --upgradeable | grep fledge | cut -d'/' -f1 > " + packageListFile;
		if (packageManager.find("yum") != std::string::npos)
		{
			command = "(sudo yum check-update && sudo yum list updates) | grep fledge | cut -d' ' -f1 > " + packageListFile;
		}	
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

	return packageList;
}

