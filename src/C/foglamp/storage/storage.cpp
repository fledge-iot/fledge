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

/**
 * Storage service main entry point
 */
int main(int argc, char *argv[])
{
	StorageService *service = new StorageService();
	service->start();
	return 0;
}

/**
 * Constructor for the storage service
 */
StorageService::StorageService()
{
unsigned short servicePort;

	config = new StorageConfiguration();
	logger = new Logger(SERVICE_NAME);

	servicePort = (unsigned short)atoi(config->getValue("port"));

	api = new StorageApi(servicePort, 1);
}

/**
 * Start the storage service
 */
void StorageService::start()
{
	if (!loadPlugin())
	{
		logger->fatal("Failed to load storage plugin.");
		return;
	}
	unsigned short managementPort = 1081;
	ManagementApi management("storage", managementPort);	// Start managemenrt API
	api->initResources();
	logger->info("Starting service...");
	api->start();
	management.registerService(this);

	management.start();


	sleep(10);
	// Now register our service
	// TODO Dynamic ports, proper hostname lookup
	unsigned short listenerPort = api->getListenerPort();
	ServiceRecord record("storage", "Storage", "http", "localhost", managementPort, listenerPort);
	ManagementClient *client = new ManagementClient("localhost", 8082);
	client->registerService(record);
	client->registerCategory(STORAGE_CATEGORY);

	// Wait for all the API threads to complete
	api->wait();

	// Clean shutdown, unregister the storage service
	client->unregisterService();
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
