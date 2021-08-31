/*
 * Fledge storage service.
 *
 * Copyright (c) 2020 Diamonic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <plugin_configuration.h>
#include <rapidjson/document.h>
#include <rapidjson/istreamwrapper.h>
#include <rapidjson/ostreamwrapper.h>
#include <rapidjson/error/en.h>
#include <rapidjson/writer.h>
#include <fstream>
#include <iostream>
#include <unistd.h>
#include <plugin_api.h>
#include <storage_plugin.h>


using namespace std;
using namespace rapidjson;

/**
 * Constructor for storage service configuration class.
 */
StoragePluginConfiguration::StoragePluginConfiguration(const string& name, StoragePlugin *plugin)
	: m_name(name), m_plugin(plugin)
{
	m_defaultConfiguration = plugin->getInfo()->config;
	m_logger = Logger::getLogger();
	m_document = new Document();
	m_category = m_name;
	readCache();
	updateCache();
}

/**
 * Return if a value exsits for the cached configuration category
 */
bool StoragePluginConfiguration::hasValue(const string& key)
{
	if (m_document->HasParseError())
	{
		m_logger->error("Default configuration failed to parse. %s at %d",
				GetParseError_En(m_document->GetParseError()),
				m_document->GetErrorOffset());
		return false;
	}
	if (!m_document->HasMember(key.c_str()))
		return false;
	return true;
}

/**
 * Return a value from the cached configuration category
 */
const char *StoragePluginConfiguration::getValue(const string& key)
{
	if (m_document->HasParseError())
	{
		m_logger->error("Default configuration failed to parse. %s at %d",
				GetParseError_En(m_document->GetParseError()),
				m_document->GetErrorOffset());
		return 0;
	}
	if (!m_document->HasMember(key.c_str()))
		return 0;
	Value& item = (*m_document)[key.c_str()];
	return item["value"].GetString();
}

/**
 * Set the value of a configuration item
 */
bool StoragePluginConfiguration::setValue(const string& key, const string& value)
{
	try {
		Value& item = (*m_document)[key.c_str()];
		const char *cstr = value.c_str();
		item["value"].SetString(cstr, strlen(cstr), m_document->GetAllocator());
		return true;
	} catch (exception e) {
		return false;
	}
}

/**
 * Called when the configuration category is updated.
 */
void StoragePluginConfiguration::updateCategory(const string& json)
{
	m_logger->info("New storage configuration %s", json.c_str());
	Document *newdoc = new Document();
	newdoc->Parse(json.c_str());
	if (newdoc->HasParseError())
	{
		m_logger->error("New configuration failed to parse. %s at %d",
				GetParseError_En(newdoc->GetParseError()),
				newdoc->GetErrorOffset());
		delete newdoc;
	}
	else
	{
		delete m_document;
		m_document = newdoc;
		writeCache();
	}
}

/**
 * Read the cache JSON for te configuration category from the cache file 
 * into memory.
 */
void StoragePluginConfiguration::readCache()
{
string	cachefile;

	getConfigCache(cachefile);
	if (access(cachefile.c_str(), F_OK ) != 0)
	{
		m_logger->info("Storage cache %s unreadable, using default configuration: %s.",
				cachefile.c_str(), m_defaultConfiguration.c_str());
		ConfigCategory confCategory("tmp", m_defaultConfiguration.c_str());
		confCategory.setItemsValueFromDefault();
		m_document->Parse(confCategory.itemsToJSON().c_str());
		if (m_document->HasParseError())
		{
			m_logger->error("Default configuration failed to parse. %s at %d",
					GetParseError_En(m_document->GetParseError()),
					m_document->GetErrorOffset());
		}
		writeCache();
		return;
	}
	try {
		ifstream ifs(cachefile);
		IStreamWrapper isw(ifs);
		m_document->ParseStream(isw);
		if (m_document->HasParseError())
		{
			m_logger->error("Default configuration failed to parse. %s at %d",
					GetParseError_En(m_document->GetParseError()),
					m_document->GetErrorOffset());
		}
	} catch (exception ex) {
		m_logger->error("Configuration cache failed to read %s.", ex.what());
	}
}

/**
 * Write the configuration cache to disk
 */
void StoragePluginConfiguration::writeCache()
{
string	cachefile;

	getConfigCache(cachefile);
	ofstream ofs(cachefile);
	OStreamWrapper osw(ofs);
	Writer<OStreamWrapper> writer(osw);
	m_document->Accept(writer);
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
void StoragePluginConfiguration::getConfigCache(string& cache)
{
char buf[512], *basedir;

	snprintf(buf, sizeof(buf), "%s.json", m_name.c_str());
	if (access(buf, F_OK) == 0)
	{
		cache = buf;
		return;
	}
	if ((basedir = getenv("FLEDGE_DATA")) != NULL)
	{
		snprintf(buf, sizeof(buf), "%s/etc/%s.json", basedir, m_name.c_str());
		if (access(buf, F_OK) == 0)
		{
			cache = buf;
			return;
		}
	}
	else if ((basedir = getenv("FLEDGE_ROOT")) != NULL)
	{
		snprintf(buf, sizeof(buf), "%s/data/etc/%s.json", basedir, m_name.c_str());
		if (access(buf, F_OK) == 0)
		{
			cache = buf;
			return;
		}
	}
	else
	{
		snprintf(buf, sizeof(buf), "%s.json", m_name.c_str());
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
DefaultConfigCategory *StoragePluginConfiguration::getDefaultCategory()
{
	StringBuffer buffer;
	Writer<StringBuffer> writer(buffer);
	m_document->Accept(writer);

	const char *config = buffer.GetString();
	return new DefaultConfigCategory(m_category, config);
}
/**
 * Return the category to register with the core. This allows
 * the storage configuration to appear in the UI
 *
 * @return ConfigCategory* The default configuration category
 */
ConfigCategory *StoragePluginConfiguration::getConfiguration()
{
	StringBuffer buffer;
	Writer<StringBuffer> writer(buffer);
	m_document->Accept(writer);

	const char *config = buffer.GetString();
	return new ConfigCategory(m_category, config);
}

/**
 * Update the cache with any new items found in the configuration returned
 * by the plugin
 */
void StoragePluginConfiguration::updateCache()
{
	Document d;
	d.Parse(m_defaultConfiguration.c_str());
	if (d.HasParseError())
	{
		m_logger->error("Configuration returned by plugin_init has parse errors");
	}
	for (auto &item : d.GetObject())
	{
		string itemName = item.name.GetString();
		if (m_document->HasMember(itemName.c_str()))
		{
		}
		else
		{
			Value v;
			v.CopyFrom(d[itemName.c_str()], m_document->GetAllocator());
			Value name;
			name.SetString(itemName.c_str(), itemName.length(), m_document->GetAllocator());
			m_document->AddMember(name, v, m_document->GetAllocator());
		}
	}
}
