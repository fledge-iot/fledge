/*
 * FogLAMP storage service.
 *
 * Copyright (c) 2017 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <configuration.h>
#include <rapidjson/document.h>
#include <rapidjson/istreamwrapper.h>
#include <rapidjson/ostreamwrapper.h>
#include <rapidjson/writer.h>
#include <fstream>
#include <iostream>
#include <unistd.h>

static const char *defaultConfiguration = " { \"plugin\" : { "
" \"value\" : \"postgres\" }, \"threads\" : { \"value\" : \"1\" },"
"  \"port\" : { \"value\" : \"8080\" }, \"managementPort\" : { \"value\" : \"1081\" } }";

using namespace std;
using namespace rapidjson;

/**
 * Constructor for storage service configuration class.
 */
StorageConfiguration::StorageConfiguration()
{
	logger = Logger::getLogger();
	readCache();
}

/**
 * Return a value from the cached configuration category
 */
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

/**
 * Set the value of a configuration item
 */
bool StorageConfiguration::setValue(const string& key, const string& value)
{
	try {
		Value& item = document[key.c_str()];
		const char *cstr = value.c_str();
		item["value"].SetString(cstr, strlen(cstr), document.GetAllocator());
		return true;
	} catch (exception e) {
		return false;
	}
}

/**
 * Called when the configuration category is updated.
 */
void StorageConfiguration::updateCategory(const string& json)
{
	document.Parse(json.c_str());
	writeCache();
}

/**
 * Read the cache JSON for te configuration category from the cache file 
 * into memory.
 */
void StorageConfiguration::readCache()
{
	if (access(CONFIGURATION_CACHE_FILE, F_OK ) != 0)
	{
		logger->info("Using default configuration: %s.", defaultConfiguration);
		document.Parse(defaultConfiguration);
		if (document.HasParseError())
		{
			logger->error("Default configuration failed to parse.");
		}
		writeCache();
		return;
	}
	try {
		ifstream ifs(CONFIGURATION_CACHE_FILE);
		IStreamWrapper isw(ifs);
		document.ParseStream(isw);
		if (document.HasParseError())
		{
			logger->error("Configuration cache failed to parse.");
		}
	} catch (exception ex) {
		logger->error("Configuration cache failed to read %s.", ex.what());
	}
}

/**
 * Write the configuration cache to disk
 */
void StorageConfiguration::writeCache()
{
	ofstream ofs(CONFIGURATION_CACHE_FILE);
	OStreamWrapper osw(ofs);
	Writer<OStreamWrapper> writer(osw);
	document.Accept(writer);
}
