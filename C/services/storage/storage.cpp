/*
 * FogLAMP storage service.
 *
 * Copyright (c) 2017 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <storage_service.h>
#include <configuration.h>
#include <management_api.h>
#include <management_client.h>
#include <service_record.h>
#include <plugin_manager.h>
#include <plugin_api.h>
#include <plugin.h>
#include <logger.h>
#include <iostream>
#include <string>

extern int makeDaemon(void);

using namespace std;

/**
 * Storage service main entry point
 */
int main(int argc, char *argv[])
{
unsigned short corePort = 8082;
string	       coreAddress = "localhost";
bool	       daemonMode = true;
string	       myName = SERVICE_NAME;
bool           returnPlugin = false;

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
		else if (!strncmp(argv[i], "--plugin", 8))
		{
			returnPlugin = true;
		}
	}

	if (returnPlugin == false && daemonMode && makeDaemon() == -1)
	{
		// Failed to run in daemon mode
		cout << "Failed to run as deamon - proceeding in interactive mode." << endl;
	}

	StorageService *service = new StorageService(myName);
	if (returnPlugin)
	{
		cout << service->getPluginName() << " " << service->getPluginManagedStatus() << endl;
	}
	else
	{
		service->start(coreAddress, corePort);
	}
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
 * Constructor for the storage service
 */
StorageService::StorageService(const string& myName) : m_name(myName), m_shutdown(false)
{
unsigned short servicePort;

	config = new StorageConfiguration();
	logger = new Logger(myName);

	if (config->getValue("port") == NULL)
	{
		servicePort = 0;	// default to a dynamic port
	}
	else
	{
		servicePort = (unsigned short)atoi(config->getValue("port"));
	}

	api = new StorageApi(servicePort, 1);
}

/**
 * Start the storage service
 */
void StorageService::start(string& coreAddress, unsigned short corePort)
{
	if (!loadPlugin())
	{
		logger->fatal("Failed to load storage plugin.");
		return;
	}
	unsigned short managementPort = (unsigned short)0;
	if (config->getValue("managementPort"))
	{
		managementPort = (unsigned short)atoi(config->getValue("managementPort"));
	}
	ManagementApi management(SERVICE_NAME, managementPort);	// Start managemenrt API
	api->initResources();
	logger->info("Starting service...");
	api->start();
	management.registerService(this);

	management.start();

	// Allow time for the listeners to start before we register
	sleep(1);
	if (! m_shutdown)
	{
		// Now register our service
		// TODO proper hostname lookup
		unsigned short listenerPort = api->getListenerPort();
		unsigned short managementListener = management.getListenerPort();
		ServiceRecord record(m_name, "Storage", "http", "localhost", listenerPort, managementListener);
		ManagementClient *client = new ManagementClient(coreAddress, corePort);
		client->registerService(record);
		unsigned int retryCount = 0;
		while (client->registerCategory(STORAGE_CATEGORY) == false && ++retryCount < 10)
		{
			sleep(2 * retryCount);
		}

		// Wait for all the API threads to complete
		api->wait();

		// Clean shutdown, unregister the storage service
		client->unregisterService();
	}
	else
	{
		api->wait();
	}
	logger->info("Storage service shut down.");
}

/**
 * Stop the storage service/
 */
void StorageService::stop()
{
	logger->info("Stopping service...\n");
}

/**
 * Load the configured storage plugin
 *
 * TODO Should search for the plugin in specified locations
 */
bool StorageService::loadPlugin()
{
	PluginManager *manager = PluginManager::getInstance();

	const char *plugin = config->getValue("plugin");
	if (plugin == NULL)
	{
		logger->error("Unable to fetch plugin name from configuration.\n");
		return false;
	}
	logger->info("Load storage plugin %s.", plugin);
	PLUGIN_HANDLE handle;
	if ((handle = manager->loadPlugin(string(plugin), PLUGIN_TYPE_STORAGE)) != NULL)
	{
		storagePlugin = new StoragePlugin(handle);
		api->setPlugin(storagePlugin);
		logger->info("Loaded storage plugin %s.", plugin);
		return true;
	}
	return false;
}

/**
 * Shutdown request
 */
void StorageService::shutdown()
{
	/* Stop recieving new requests and allow existing
	 * requests to drain.
	 */
	m_shutdown = true;
	logger->info("Storage service shutdown in progress.");
	api->stopServer();
}

/**
 * Configuration change notification
 */
void StorageService::configChange(const string& categoryName, const string& category)
{
	if (!categoryName.compare(STORAGE_CATEGORY))
	{
		config->updateCategory(category);
	}
}

/**
 * Return the name of the configured storage service
 */
string StorageService::getPluginName()
{
	return string(config->getValue("plugin"));
}

/**
 * Return the managed status of the storage plugin
 */
string StorageService::getPluginManagedStatus()
{
	return string(config->getValue("managedStatus"));
}
