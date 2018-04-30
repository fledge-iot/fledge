/*
 * FogLAMP storage service.
 *
 * Copyright (c) 2018 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <south_service.h>
#include <management_api.h>
#include <management_client.h>
#include <storage_client.h>
#include <service_record.h>
#include <plugin_manager.h>
#include <plugin_api.h>
#include <plugin.h>
#include <logger.h>
#include <reading.h>
#include <ingest.h>
#include <iostream>

extern int makeDaemon(void);

using namespace std;

/**
 * South service main entry point
 */
int main(int argc, char *argv[])
{
unsigned short corePort = 8082;
string	       coreAddress = "localhost";
bool	       daemonMode = true;
string	       myName = SERVICE_NAME;

	for (int i = 1; i < argc; i++)
	{
		if (!strcmp(argv[i], "-d"))
		{
			daemonMode = false;
		}
		else if (!strncmp(argv[i], "--port=", 7))
		{
			corePort = (unsigned short)atoi(&argv[i][7]);
		}
		else if (!strncmp(argv[i], "--name=", 7))
		{
			myName = &argv[i][7];
		}
		else if (!strncmp(argv[i], "--address=", 10))
		{
			coreAddress = &argv[i][10];
		}
	}

	if (daemonMode && makeDaemon() == -1)
	{
		// Failed to run in daemon mode
		cout << "Failed to run as deamon - proceeding in interactive mode." << endl;
	}

	SouthService *service = new SouthService(myName);
	service->start(coreAddress, corePort);
	return 0;
}

/**
 * Detach the process from the terminal and run in the background.
 */
int makeDaemon()
{
pid_t pid;

	/* create new process */
	if ((pid = fork()  ) == -1)
	{
		return -1;  
	}
	else if (pid != 0)  
	{
		exit (EXIT_SUCCESS);  
	}

	// If we got here we are a child process

	// create new session and process group 
	if (setsid() == -1)  
	{
		return -1;  
	}

	// Close stdin, stdout and stderr
	close(0);
	close(1);
	close(2);
	// redirect fd's 0,1,2 to /dev/null
	(void)open("/dev/null", O_RDWR);  	// stdin
	(void)dup(0);  			// stdout	GCC bug 66425 produces warning
	(void)dup(0);  			// stderr	GCC bug 66425 produces warning
 	return 0;
}

/**
 * Constructor for the south service
 */
SouthService::SouthService(const string& myName) : m_name(myName), m_shutdown(false)
{
	logger = new Logger(myName);
}

/**
 * Start the south service
 */
void SouthService::start(string& coreAddress, unsigned short corePort)
{
	if (!loadPlugin())
	{
		logger->fatal("Failed to load south plugin.");
		return;
	}
	unsigned short managementPort = (unsigned short)0;
	ManagementApi management(SERVICE_NAME, managementPort);	// Start managemenrt API
	logger->info("Starting south service...");
	management.registerService(this);

	// Listen for incomming managment requests
	management.start();

	// Allow time for the listeners to start before we register
	sleep(1);
	if (! m_shutdown)
	{
		// Now register our service
		// TODO proper hostname lookup
		unsigned short managementListener = management.getListenerPort();
		ServiceRecord record(m_name, "Southbound", "http", "localhost", 0, managementListener);
		ManagementClient *client = new ManagementClient(coreAddress, corePort);
		if (!client->registerService(record))
		{
			logger->error("Failed to register service %s", m_name.c_str());
		}
		unsigned int retryCount = 0;
		while (client->registerCategory(m_name) == false && ++retryCount < 10)
		{
			sleep(2 * retryCount);
		}

		// Get a handle on the storage layer
		ServiceRecord storageRecord("FogLAMP%20Storage");
		if (!client->getService(storageRecord))
		{
			logger->fatal("Unable to find storage service");
			return;
		}
		logger->info("Connect to storage on %s:%d",
				storageRecord.getAddress().c_str(),
				storageRecord.getPort());

		
		StorageClient storage(storageRecord.getAddress(),
						storageRecord.getPort());
		Ingest ingest(storage);

		while (! m_shutdown)
		{
			sleep(1);
			Reading reading = southPlugin->poll();
			ingest.ingest(reading);
		}

		// Clean shutdown, unregister the storage service
		client->unregisterService();
	}
	logger->info("South service shut down.");
}

/**
 * Stop the storage service/
 */
void SouthService::stop()
{
	logger->info("Stopping south service...\n");
}

/**
 * Load the configured south plugin
 *
 * TODO Should search for the plugin in specified locations
 */
bool SouthService::loadPlugin()
{
	PluginManager *manager = PluginManager::getInstance();

	const char *plugin = "dummy";
	if (plugin == NULL)
	{
		logger->error("Unable to fetch plugin name from configuration.\n");
		return false;
	}
	logger->info("Load south plugin %s.", plugin);
	PLUGIN_HANDLE handle;
	if ((handle = manager->loadPlugin(string(plugin), PLUGIN_TYPE_SOUTH)) != NULL)
	{
		southPlugin = new SouthPlugin(handle);
		logger->info("Loaded south plugin %s.", plugin);
		return true;
	}
	return false;
}

/**
 * Shutdown request
 */
void SouthService::shutdown()
{
	/* Stop recieving new requests and allow existing
	 * requests to drain.
	 */
	m_shutdown = true;
	logger->info("South service shutdown in progress.");
}

/**
 * Configuration change notification
 */
void SouthService::configChange(const string& categoryName, const string& category)
{
    // TODO action configuration change
}
