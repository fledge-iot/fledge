#include <configuration.h>
#include <rapidjson/document.h>
#include <rapidjson/istreamwrapper.h>
#include <fstream>
#include <iostream>

using namespace std;
using namespace rapidjson;

/**
 * Constructor for storage service configuration class.
 */
StorageConfiguration::StorageConfiguration()
{
  readCache();
  logger = Logger::getLogger();
}

const char *StorageConfiguration::getValue(const string& key)
{
  if (document.HasParseError())
  {
    logger->error("Configuration cache failed to parse.");
    return 0;
  }
  if (!document.HasMember(key.c_str()))
    return 0;
  Value& item = document[key.c_str()];
  return item["value"].GetString();
}

bool StorageConfiguration::setValue(const string& key, const string& value)
{
  return false;
}

void StorageConfiguration::updateCategory(const string& json)
{
}

void StorageConfiguration::readCache()
{
  try {
  ifstream ifs(CONFIGURATION_CACHE_FILE);
  IStreamWrapper isw(ifs);
  document.ParseStream(isw);
  if (document.HasParseError())
  if (document.HasParseError())
  {
    logger->error("Configuration cache failed to parse.");
  }
  } catch (exception ex) {
    logger->error("Configuration cache failed to read %s.", ex.what());
  }
}

void StorageConfiguration::writeCache()
{
}
