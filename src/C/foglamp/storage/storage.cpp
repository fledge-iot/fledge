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
	config = new StorageConfiguration();
	logger = new Logger(SERVICE_NAME);

	api = new StorageApi(8080, 1);
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
	ManagementApi management("storage", 1081);	// Start managemenrt API on port 8081
	api->initResources();
	logger->info("Starting service...");
	api->start();

	management.start();


	// Now register our service
	// TODO Dynamic ports, proper hostname lookup
	ServiceRecord record("storage", "Storage", "http", "localhost", 8080);
	ManagementClient *client = new ManagementClient("localhost", 8082);
	client->registerService(record);

	api->wait();
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
