#include <storage_service.h>
#include <configuration.h>
#include <plugin_manager.h>
#include <plugin_api.h>
#include <plugin.h>
#include <logger.h>

int main(int argc, char *argv[])
{
  StorageService *service = new StorageService();
  service->start();
  return 0;
}

StorageService::StorageService()
{
  config = new StorageConfiguration();
  logger = new Logger(SERVICE_NAME);

	api = new StorageApi(8080, 1);
}

void StorageService::start()
{
  if (!loadPlugin())
  {
    logger->fatal("Failed to load storage plugin.");
    return;
  }
  api->initResources();
  logger->info("Starting service...");
	api->start();

	api->wait();
}

void StorageService::stop()
{
  logger->info("Stopping service...\n");
}

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
