/*
 * FogLAMP storage service.
 *
 * Copyright (c) 2017-2018 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch, Massimiliano Pinto
 */
#include <configuration.h>
#include <rapidjson/document.h>
#include <rapidjson/istreamwrapper.h>
#include <rapidjson/ostreamwrapper.h>
#include <rapidjson/writer.h>
#include <fstream>
#include <iostream>
#include <unistd.h>

static const char *defaultConfiguration =
" { \"plugin\" : { \"value\" : \"postgres\", \"description\" : \"The storage plugin to load\"},"
" \"threads\" : { \"value\" : \"1\", \"description\" : \"The number of threads to run\" },"
" \"managedStatus\" : { \"value\" : \"false\", \"description\" : \"Control if FogLAMP should manage the storage provider\" },"
" \"port\" : { \"value\" : \"0\", \"description\" : \"The port to listen on\" },"
" \"managementPort\" : { \"value\" : \"0\", \"description\" : \"The management port to listen on.\" } }";

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
string	cachefile;

	getConfigCache(cachefile);
	if (access(cachefile.c_str(), F_OK ) != 0)
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
		ifstream ifs(cachefile);
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
string	cachefile;

	getConfigCache(cachefile);
	ofstream ofs(cachefile);
	OStreamWrapper osw(ofs);
	Writer<OStreamWrapper> writer(osw);
	document.Accept(writer);
}

/**
 * Retrieve the location of the configuration cache to use
 *
 * If a configuration cache exists in the current directory then it is used
 *
 * If not and the environment variable FOGLAMP_DATA exists then the
 * configuration file under etc in that directory will be used.
 *
 * If that does not exist and the configuration variable FOGLAMP_HONE
 * exists then a configuration file under etc in that dirstory is used
 */
void StorageConfiguration::getConfigCache(string& cache)
{
char buf[512], *basedir;

	if (access(CONFIGURATION_CACHE_FILE, F_OK) == 0)
	{
		cache = CONFIGURATION_CACHE_FILE;
		return;
	}
	if ((basedir = getenv("FOGLAMP_DATA")) != NULL)
	{
		snprintf(buf, sizeof(buf), "%s/etc/%s", basedir, CONFIGURATION_CACHE_FILE);
		if (access(buf, F_OK) == 0)
		{
			cache = buf;
			return;
		}
	}
	else if ((basedir = getenv("FOGLAMP_ROOT")) != NULL)
	{
		snprintf(buf, sizeof(buf), "%s/etc/%s", basedir, CONFIGURATION_CACHE_FILE);
		if (access(buf, F_OK) == 0)
		{
			cache = buf;
			return;
		}
	}
	else
	{
		snprintf(buf, sizeof(buf), "%s", CONFIGURATION_CACHE_FILE);
	}

	// No configuration cache has been found - return the default location
	cache = buf;
}
