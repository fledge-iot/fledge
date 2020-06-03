/*
 * Fledge storage service.
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
#include <rapidjson/error/en.h>
#include <rapidjson/writer.h>
#include <fstream>
#include <iostream>
#include <unistd.h>
#include <plugin_api.h>

static const char *defaultConfiguration = QUOTE({
	"plugin" : {
       		"value" : "sqlite",
		"default" : "sqlite",
		"description" : "The main storage plugin to load",
		"type" : "string",
		"displayName" : "Storage Plugin",
		"order" : "1"
		},
	"readingPlugin" : {
		"value" : "",
		"default" : "",
		"description" : "The storage plugin to load for readings data. If blank the main storage plugin is used.",
		"type" : "string",
		"displayName" : "Readings Plugin",
		"order" : "2"
		},
	"threads" : {
	       	"value" : "1", 
		"default" : "1",
		"description" : "The number of threads to run",
		"type" : "integer",
		"displayName" : "Database threads",
		"order" : "3"
	       	},
	"managedStatus" : {
		"value" : "false",
		"default" : "false",
		"description" : "Control if Fledge should manage the storage provider",
		"type" : "boolean",
		"displayName" : "Manage Storage",
		"order" : "4"
		},
	"port" : { 
		"value" : "0",
		"default" : "0",
		"description" : "The port to listen on",
		"type" : "integer",
		"displayName" : "Service Port",
		"order" : "5"
	},
	"managementPort" : {
		"value" : "0", 
		"default" : "0",
		"description" : "The management port to listen on.",
		"type" : "integer",
		"displayName" : "Management Port",
		"order" : "6"
       	}
});

using namespace std;
using namespace rapidjson;

/**
 * Constructor for storage service configuration class.
 */
StorageConfiguration::StorageConfiguration()
{
	logger = Logger::getLogger();
	document = new Document();
	readCache();
	checkCache();
}

/**
 * Return if a value exsits for the cached configuration category
 */
bool StorageConfiguration::hasValue(const string& key)
{
	if (document->HasParseError())
	{
		logger->error("Default configuration failed to parse. %s at %d",
				GetParseError_En(document->GetParseError()),
				document->GetErrorOffset());
		return false;
	}
	if (!document->HasMember(key.c_str()))
		return false;
	return true;
}

/**
 * Return a value from the cached configuration category
 */
const char *StorageConfiguration::getValue(const string& key)
{
	if (document->HasParseError())
	{
		logger->error("Default configuration failed to parse. %s at %d",
				GetParseError_En(document->GetParseError()),
				document->GetErrorOffset());
		return 0;
	}
	if (!document->HasMember(key.c_str()))
		return 0;
	Value& item = (*document)[key.c_str()];
	return item["value"].GetString();
}

/**
 * Set the value of a configuration item
 */
bool StorageConfiguration::setValue(const string& key, const string& value)
{
	try {
		Value& item = (*document)[key.c_str()];
		const char *cstr = value.c_str();
		item["value"].SetString(cstr, strlen(cstr), document->GetAllocator());
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
	logger->info("New storage configuration %s", json.c_str());
	Document *newdoc = new Document();
	newdoc->Parse(json.c_str());
	if (newdoc->HasParseError())
	{
		logger->error("New configuration failed to parse. %s at %d",
				GetParseError_En(newdoc->GetParseError()),
				newdoc->GetErrorOffset());
		delete newdoc;
	}
	else
	{
		delete document;
		document = newdoc;
		writeCache();
	}
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
		document->Parse(defaultConfiguration);
		if (document->HasParseError())
		{
			logger->error("Default configuration failed to parse. %s at %d",
					GetParseError_En(document->GetParseError()),
					document->GetErrorOffset());
		}
		writeCache();
		return;
	}
	try {
		ifstream ifs(cachefile);
		IStreamWrapper isw(ifs);
		document->ParseStream(isw);
		if (document->HasParseError())
		{
			logger->error("Default configuration failed to parse. %s at %d",
					GetParseError_En(document->GetParseError()),
					document->GetErrorOffset());
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
	document->Accept(writer);
}

/**
 * Retrieve the location of the configuration cache to use
 *
 * If a configuration cache exists in the current directory then it is used
 *
 * If not and the environment variable FLEDGE_DATA exists then the
 * configuration file under etc in that directory will be used.
 *
 * If that does not exist and the configuration variable FLEDGE_HONE
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
	if ((basedir = getenv("FLEDGE_DATA")) != NULL)
	{
		snprintf(buf, sizeof(buf), "%s/etc/%s", basedir, CONFIGURATION_CACHE_FILE);
		if (access(buf, F_OK) == 0)
		{
			cache = buf;
			return;
		}
	}
	else if ((basedir = getenv("FLEDGE_ROOT")) != NULL)
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

/**
 * Return the default category to register with the core. This allows
 * the storage configuration to appear in the UI
 *
 * @return DefaultConfigCategory* The default configuration category
 */
DefaultConfigCategory *StorageConfiguration::getDefaultCategory()
{
	StringBuffer buffer;
	Writer<StringBuffer> writer(buffer);
	document->Accept(writer);

	const char *config = buffer.GetString();
	return new DefaultConfigCategory(STORAGE_CATEGORY, config);
}

/**
 * One off check for upgrade to cache that has full UI information
 *
 * This is only really triggered when we first do an upgrade from the
 * older cache files to the current JSON defaults that contains the
 * full information needed for the GUI.
 */
void StorageConfiguration::checkCache()
{

	if (document->HasMember("plugin"))	
	{
		Value& item = (*document)["plugin"];
		if (item.HasMember("type"))
		{
			logger->info("Storage configuration cache is up to date");
			return;
		}
	}
	logger->info("Storage configuration cache is not up to date");
	Document *newdoc = new Document();
	newdoc->Parse(defaultConfiguration);
	if (newdoc->HasParseError())
	{
		logger->error("Default configuration failed to parse. %s at %d",
				GetParseError_En(document->GetParseError()),
				newdoc->GetErrorOffset());
	}
	for (Value::ConstMemberIterator itr = newdoc->MemberBegin();
				itr != newdoc->MemberEnd(); ++itr)
	{
		const char *name = itr->name.GetString();
		Value &newval = (*newdoc)[name];
		if (hasValue(name))
		{
			const char *val = getValue(name);
			newval["value"].SetString(strdup(val), strlen(val));
		}
	}
	delete document;
	document = newdoc;
	writeCache();
}
