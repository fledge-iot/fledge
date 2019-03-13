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
#include <signal.h>
#include <dlfcn.h>
#include <execinfo.h>
#include <cxxabi.h>


#define LOG_SERVICE_NAME  "FogLAMP Process"

using namespace std;

/**
 * Signal handler to log stack traces on fatal signals
 */
static void handler(int sig)
{
Logger	*logger = Logger::getLogger();
void	*array[20];
char	buf[1024];
int	size;

	// get void*'s for all entries on the stack
	size = backtrace(array, 20);

	// print out all the frames to stderr
	logger->fatal("Signal %d (%s) trapped:\n", sig, strsignal(sig));
	char **messages = backtrace_symbols(array, size);
	for (int i = 0; i < size; i++)
	{
		Dl_info info;
		if (dladdr(array[i], &info) && info.dli_sname)
		{
		    char *demangled = NULL;
		    int status = -1;
		    if (info.dli_sname[0] == '_')
		        demangled = abi::__cxa_demangle(info.dli_sname, NULL, 0, &status);
		    snprintf(buf, sizeof(buf), "%-3d %*p %s + %zd---------",
		             i, int(2 + sizeof(void*) * 2), array[i],
		             status == 0 ? demangled :
		             info.dli_sname == 0 ? messages[i] : info.dli_sname,
		             (char *)array[i] - (char *)info.dli_saddr);
		    free(demangled);
		} 
		else
		{
		    snprintf(buf, sizeof(buf), "%-3d %*p %s---------",
		             i, int(2 + sizeof(void*) * 2), array[i], messages[i]);
		}
		logger->fatal("(%d) %s", i, buf);
	}
	free(messages);
	exit(1);
}

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
	signal(SIGSEGV, handler);
	signal(SIGILL, handler);
	signal(SIGBUS, handler);
	signal(SIGFPE, handler);
	signal(SIGABRT, handler);

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

	m_logger->setMinLevel("warning");	// Default to warnings, errors and fatal for log messages
	try
	{
		string minLogLevel = getArgValue("--loglevel=");
		if (!minLogLevel.empty())
		{
			m_logger->setMinLevel(minLogLevel);
		}
	}
	catch (exception e)
	{
		throw runtime_error(string("Error while parsing optional options: ") + e.what());
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
