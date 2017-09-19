#include <plugin.h>
#include <plugin_manager.h>

Plugin::Plugin(PLUGIN_HANDLE handle)
{
  this->handle = handle;
  this->manager = PluginManager::getInstance();
  this->info = this->manager->getInfo(handle);
}

Plugin::~Plugin()
{
}

const PLUGIN_INFORMATION *Plugin::getInfo()
{
  return this->info;
}
