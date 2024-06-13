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
#include <unordered_set>
#include <unistd.h>
#include <plugin_api.h>
#include <plugin_manager.h>

static std::string defaultConfiguration(QUOTE({
	"plugin" : {
		"value" : "sqlite",
		"default" : "sqlite",
		"description" : "The main storage plugin to load",
		"type" : "enumeration",
		"options" : [ "sqlite", "sqlitelb", "postgres" ],
		"displayName" : "Storage Plugin",
		"order" : "1"
		},
	"readingPlugin" : {
		"value" : "Use main plugin",
		"default" : "Use main plugin",
		"description" : "The storage plugin to load for readings data.",
		"type" : "enumeration",
		"options" : [ "Use main plugin", "sqlite", "sqlitelb", "sqlitememory", "postgres" ],
		"displayName" : "Readings Plugin",
		"order" : "2"
		},
	"threads" : {
	       	"value" : "1", 
		"default" : "1",
		"description" : "The number of threads to use for the storage API",
		"type" : "integer",
		"displayName" : "Storage API threads",
		"minimum" : "1",
		"maximum" : "10",
		"order" : "3"
	       	},
	"workerPool" : {
	       	"value" : "5", 
		"default" : "5",
		"description" : "The number of threads to create in the thread pool used to execute operations against reading data",
		"type" : "integer",
		"displayName" : "Worker thread pool",
		"minimum" : "1",
		"maximum" : "10",
		"order" : "4"
	       	},
	"managedStatus" : {
		"value" : "false",
		"default" : "false",
		"description" : "Control if Fledge should manage the storage provider",
		"type" : "boolean",
		"displayName" : "Manage Storage",
		"order" : "5"
		},
	"port" : { 
		"value" : "0",
		"default" : "0",
		"description" : "The port to listen on",
		"type" : "integer",
		"displayName" : "Service Port",
		"order" : "6"
	},
	"managementPort" : {
		"value" : "0", 
		"default" : "0",
		"description" : "The management port to listen on.",
		"type" : "integer",
		"displayName" : "Management Port",
		"order" : "7"
       	},
	"logLevel" : {
		"value" : "warning",
		"default" : "warning",
		"description" : "Minimum level of messages to log",
		"type" : "enumeration",
		"displayName" : "Log Level",
		"options" : [ "error", "warning", "info", "debug" ],
		"order" : "8"
	},
	"timeout" : {
		"value" : "60",
		"default" : "60",
		"description" : "Server request timeout, expressed in seconds",
		"type" : "integer",
		"displayName" : "Timeout",
		"order" : "9",
		"minimum" : "5",
		"maximum" : "3600"
	},
	"perfmon": {
		"description": "Track and store performance counters",
		"type": "boolean",
		"displayName": "Performance Counters",
		"default": "false",
		"value": "false",
		"order" : "10"
	}
}));

using namespace std;
using namespace rapidjson;

/**
 * Constructor for storage service configuration class.
 */
StorageConfiguration::StorageConfiguration()
{
	logger = Logger::getLogger();
	document = new Document();
	/**
	 * Update options in deafult configuration for items 'plugin' and 
	 * 'readingPlugin' with installed plugins
	 */
	updateStoragePluginConfig();

	readCache();
	checkCache();
	if (hasValue("logLevel"))
	{
		logger->setMinLevel(getValue("logLevel"));
	}
}

/**
 * Storage configuration destructor
 */
StorageConfiguration::~StorageConfiguration()
{
	delete document;
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
	} catch (...) {
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
		logger->info("Storage cache %s unreadable, using default configuration: %s.",
				cachefile.c_str(), defaultConfiguration.c_str());

		document->Parse(defaultConfiguration.c_str());
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
	} catch (exception& ex) {
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
		snprintf(buf, sizeof(buf), "%s/data/etc/%s", basedir, CONFIGURATION_CACHE_FILE);
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
 *
 * FOGL-4151 After changing to a new plugin, say from sqlite to postgres, the first
 * time we run in the new database there is no configuraion category. In this case we will
 * get the default category, which will have a default of sqlite and no value. This will
 * end up reporting the wrong information in the UI when we look at the category, therefore
 * we special case the plugin name and set the default to whatever the current value is
 * for just this property.
 *
 * FOGL-7074 Make the plugin selection an enumeration
 */
void StorageConfiguration::checkCache()
{
bool forceUpdate = false;
bool writeCacheRequired = false;

	/*
	 * If the cached version of the configuFration that has been read in
	 * does not contain an item in the default configuration, then copy
	 * that item from the default configuration.
	 *
	 * This allows new tiems to be added to the configuration and populated
	 * in the cache on first restart.
	 */
	Document *newdoc = new Document();
	newdoc->Parse(defaultConfiguration.c_str());
	if (newdoc->HasParseError())
	{
		logger->error("Default configuration failed to parse. %s at %d",
				GetParseError_En(document->GetParseError()),
				newdoc->GetErrorOffset());
	}
	else
	{
		for (Value::ConstMemberIterator itr = newdoc->MemberBegin();
				itr != newdoc->MemberEnd(); ++itr)
		{
			const char *name = itr->name.GetString();
			Value &newval = (*newdoc)[name];
			if (!hasValue(name))
			{
				logger->warn("Adding storage configuration item %s from defaults", name);
				Document::AllocatorType& a = document->GetAllocator();
				Value copy(name, a);
				copy.CopyFrom(newval, a);
				Value n(name, a);
				document->AddMember(n, copy, a);
				writeCacheRequired = true;
			}
		}

		// if storage plugins are updated after cache is created, update exisitng cache
		// with new/removed plugins
		if (document->HasMember("plugin") && newdoc->HasMember("plugin"))
		{
			Value& currentItem = (*newdoc)["plugin"];
			Value& cacheItem = (*document)["plugin"];
			// check for difference between cached plugin options and 
			// currently installed storage plugins
			unordered_set<std::string>cacheOptions;
			unordered_set<std::string>currentOptions;
			
			// build list of plugins
			for (auto& options : currentItem["options"].GetArray())
			{
				currentOptions.insert(options.GetString());
			}
			if (cacheItem.HasMember("options") && cacheItem["options"].IsArray())
			{
				for (auto& options : cacheItem["options"].GetArray())
				{
					if (options.IsString()) 
					{
						cacheOptions.insert(options.GetString());
					}
				}
			}
			// check for difference between cached and current plugins
			bool updateOptions = false;
			if (cacheOptions.size() != currentOptions.size()) 
			{
				updateOptions = true;
			} 
			else 
			{
				for (const std::string& element : currentOptions) {
					if (cacheOptions.find(element) == cacheOptions.end()) {
						updateOptions = true;
						break;
					}
				}

			}
			if (updateOptions) 
			{
				// Update cached plugins option
				Document::AllocatorType& a = document->GetAllocator();
				cacheItem["options"].SetArray();
				for (auto& option : currentOptions)
				{
					cacheItem["options"].PushBack(Value().SetString(option.c_str(),a), a);
				}
				writeCacheRequired = true;
			}
		}

		if (document->HasMember("readingPlugin") && newdoc->HasMember("readingPlugin"))
		{
			Value& currentItem = (*newdoc)["readingPlugin"];
			Value& cacheItem = (*document)["readingPlugin"];
			// check for difference between cached plugin options and 
			// currently installed storage plugins
			unordered_set<std::string>cacheOptions;
			unordered_set<std::string>currentOptions;
			
			// build list of plugins
			for (auto& options : currentItem["options"].GetArray())
			{
				currentOptions.insert(options.GetString());
			}
			if (cacheItem.HasMember("options") && cacheItem["options"].IsArray())
			{
				for (auto& options : cacheItem["options"].GetArray())
				{
					if (options.IsString()) 
					{
						cacheOptions.insert(options.GetString());
					}
				}
			}
			// check for difference between cached and current plugins
			bool updateOptions = false;
			if (cacheOptions.size() != currentOptions.size()) 
			{
				updateOptions = true;
			} 
			else 
			{
				for (const std::string& element : currentOptions) {
					if (cacheOptions.find(element) == cacheOptions.end()) {
						updateOptions = true;
						break;
					}
				}

			}
			if (updateOptions) 
			{
				// Update cached plugins option
				Document::AllocatorType& a = document->GetAllocator();
				cacheItem["options"].SetArray();
				for (auto& option : currentOptions)
				{
					cacheItem["options"].PushBack(Value().SetString(option.c_str(),a), a);
				}
				writeCacheRequired = true;
			}
		}
	}

	delete newdoc;

	if (writeCacheRequired)
	{
		// We added a new member
		writeCache();
	}

	// Upgrade step to add eumeration for plugin
	if (document->HasMember("plugin"))
	{
		Value& item = (*document)["plugin"];
		if (item.HasMember("type") && item["type"].IsString())
		{
			const char *type = item["type"].GetString();
			if (strcmp(type, "enumeration"))
			{
				// It's not an enumeration currently
				forceUpdate = true;
			}
		}
	}

	// Cache is from before we used an enumeration for the plugin, force upgrade
	// steps
	if (forceUpdate == false && document->HasMember("plugin"))
	{
		logger->info("Adding database plugin enumerations");
		Value& item = (*document)["plugin"];
		if (item.HasMember("type"))
		{
			const char *val = getValue("plugin");
			item["default"].SetString(val, strlen(val));
			Value& rp = (*document)["readingPlugin"];
			const char *rval = getValue("readingPlugin");
			if (strlen(rval) == 0)
			{
				rval = "Use main plugin";
			}
			char *ncrval = strdup(rval);
			rp["default"].SetString(ncrval, strlen(rval));
			rp["value"].SetString(ncrval, strlen(rval));
			logger->info("Storage configuration cache is up to date");
			return;
		}
	}

	logger->info("Storage configuration cache is not up to date");
	newdoc = new Document();
	newdoc->Parse(defaultConfiguration.c_str());
	if (newdoc->HasParseError())
	{
		logger->error("Default configuration failed to parse. %s at %d",
				GetParseError_En(document->GetParseError()),
				newdoc->GetErrorOffset());
	}
	else
	{
		for (Value::ConstMemberIterator itr = newdoc->MemberBegin();
				itr != newdoc->MemberEnd(); ++itr)
		{
			const char *name = itr->name.GetString();
			Value &newval = (*newdoc)[name];
			if (hasValue(name))
			{
				const char *val = getValue(name);
				newval["value"].SetString(strdup(val), strlen(val));
				if (strcmp(name, "plugin") == 0)
				{
					newval["default"].SetString(strdup(val), strlen(val));
					logger->warn("Set default of %s to %s", name, val);
				}
				if (strcmp(name, "readingPlugin") == 0)
				{
					if (strlen(val) == 0)
					{
						val = "Use main plugin";
					}
					newval["default"].SetString(strdup(val), strlen(val));
					logger->warn("Set default of %s to %s", name, val);
				}
			}
		}
	}
	delete document;
	document = newdoc;
	writeCache();
}

/**
 * Check for installed storage and readings plugin and update default configuration.
 * 
 * Update options for category item 'plugin' and 'readingPlugin' 
 * with installed plugins.
 * 
 * If no plugin is found default config is not updated.
 * 
 * For plugins installed after cache is created options is updated via checkCache on restart
 */
void StorageConfiguration::updateStoragePluginConfig()
{
	PluginManager *manager = PluginManager::getInstance();
	manager->setPluginType(PLUGIN_TYPE_ID_STORAGE);

	// Fetch installed storage and readings plugins.
	auto storagePlugins = manager->getPluginsByFlags(PLUGIN_TYPE_STORAGE, SP_COMMON);
	auto readingsPlugins = manager->getPluginsByFlags(PLUGIN_TYPE_STORAGE, SP_READINGS);
	
	Document newDocument;
	newDocument.Parse(defaultConfiguration.c_str());

	if (storagePlugins.size() > 0) 
	{
		// Modify the "options" array for storage with installed plugins
		if (newDocument.HasMember("plugin") && newDocument["plugin"].IsObject()) {
			Value& plugin = newDocument["plugin"];
			if (plugin.HasMember("options") && plugin["options"].IsArray()) {
				Value& options = plugin["options"];
				options.Clear();
				for (const auto& option : storagePlugins) 
				{
					options.PushBack(Value().SetString(option.c_str(), newDocument.GetAllocator()), newDocument.GetAllocator());
				}
			}
		}
	} else {
		logger->debug("unable to find installed storage plugins");
	}

	if (readingsPlugins.size() > 0) 
	{
		// Modify the "options" array for readingsPlugin with installed plugins
		if (newDocument.HasMember("readingPlugin") && newDocument["readingPlugin"].IsObject()) 
		{
			Value& plugin = newDocument["readingPlugin"];
			if (plugin.HasMember("options") && plugin["options"].IsArray()) 
			{
				Value& options = plugin["options"];
				options.Clear();
				// Add default option "Use main plugin"
				options.PushBack(Value().SetString("Use main plugin", newDocument.GetAllocator()), newDocument.GetAllocator());
				for (const auto& option : readingsPlugins) 
				{
					options.PushBack(Value().SetString(option.c_str(), newDocument.GetAllocator()), newDocument.GetAllocator());
				}
			}
		}
	} else {
		logger->debug("unable to find installed readings plugins");
	}

	// Update default configuration if options are modified
	if (storagePlugins.size() > 0 || readingsPlugins.size() > 0) 
	{
		StringBuffer buffer;
		Writer<StringBuffer> writer(buffer);
		newDocument.Accept(writer);
		defaultConfiguration = buffer.GetString();
	}
}
