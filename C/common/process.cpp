/*
 * FogLAMP process class
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Massimiliano Pinto
 */

/**
 * FogLAMP process base class
 */
#include <iostream>
#include <logger.h>
#include <process.h>
#include <service_record.h>

#define LOG_SERVICE_NAME  "FogLAMP Process"

using namespace std;

// Destructor
FogLampProcess::~FogLampProcess()
{
	delete m_client;
	delete m_storage;
	delete m_logger;
}

// Constructor
FogLampProcess::FogLampProcess(int argc, char** argv) :
				m_stime(time(NULL)),
				m_argc(argc),
				m_arg_vals((const char**) argv)
{
	string myName = LOG_SERVICE_NAME;
	m_logger = new Logger(myName);

	try
	{
		m_core_mngt_host = getArgValue("--address=");
		m_core_mngt_port = atoi(getArgValue("--port=").c_str());
		m_name = getArgValue("--name=");
	}
	catch (exception e)
	{
		throw runtime_error(string("Error while parsing required options: ") + e.what());
	}

	if (m_core_mngt_host.empty())
	{
		throw runtime_error("Error: --address is not specified");
	}
	else if (m_core_mngt_port == 0)
	{
		throw runtime_error("Error: --port is not specified");
	}
	else if (m_name.empty())
	{
		throw runtime_error("Error: --name is not specified");
	}

	// Connection to FogLamp core microservice
	m_client = new ManagementClient(m_core_mngt_host, m_core_mngt_port);

	// Storage layer handle
	ServiceRecord storageInfo("FogLAMP Storage");

	if (!m_client->getService(storageInfo))
	{
		string errMsg("Unable to find storage service at ");
		errMsg += m_core_mngt_host;
		errMsg += ':';
		errMsg += to_string(m_core_mngt_port);

		throw runtime_error(errMsg);
	}

	if (!(m_storage = new StorageClient(storageInfo.getAddress(),
					    storageInfo.getPort())))
	{
		string errMsg("Unable to connect to storage service at ");
		errMsg.append(storageInfo.getAddress());
		errMsg += ':';
		errMsg += to_string(storageInfo.getPort());

		throw runtime_error(errMsg);
	}
}

/**
 * Get command line argument value like "--xyx=ABC"
 * Argument name to pass is "--xyz="
 *
 * @param name    The argument name (--xyz=)
 * @return        The argument value if found or an emopty string
 */
string FogLampProcess::getArgValue(const string& name) const
{
	for (int i=1; i < m_argc; i++)
	{
		if (strncmp(m_arg_vals[i], name.c_str(), name.length()) == 0)
		{
			// Return the option value (after "--xyx=ABC"
			return string(m_arg_vals[i] + name.length());
		}
	}
	// Return empty string
	return string("");
}

/**
 * Return storage client
 */
StorageClient* FogLampProcess::getStorageClient() const
{
        return m_storage;
}

/**
 * Return management client
 */
ManagementClient* FogLampProcess::getManagementClient() const
{
	return m_client;
}

/**
 * Return Logger
 */
Logger *FogLampProcess::getLogger() const
{
	return m_logger;
}
