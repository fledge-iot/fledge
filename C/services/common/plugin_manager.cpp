/*
 * Fledge plugin manager.
 *
 * Copyright (c) 2017, 2018 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch, Massimiliano Pinto
 */
#include <cstdio>
#include <dlfcn.h>
#include <string.h>
#include <iostream>
#include <fstream>
#include <unistd.h>
#include <plugin_manager.h>
#include <binary_plugin_handle.h>
#include <south_python_plugin_handle.h>
#include <north_python_plugin_handle.h>
#include <notification_python_plugin_handle.h>
#include <filter_python_plugin_handle.h>
#include <dirent.h>
#include <sys/param.h>
#include "rapidjson/document.h"
#include "rapidjson/writer.h"
#include "rapidjson/stringbuffer.h"
#include "rapidjson/error/error.h"
#include "rapidjson/error/en.h"
#include <algorithm>
#include <config_category.h>
#include <string_utils.h>

using namespace std;
using namespace rapidjson;

PluginManager *PluginManager::instance = 0;

typedef PLUGIN_INFORMATION *(*func_t)();

/**
 * PluginManager Singleton implementation
*/
PluginManager *PluginManager::getInstance()
{
  if (!instance)
    instance = new PluginManager();
  return instance;
}

/**
 * Plugin Manager Constructor
 */
PluginManager::PluginManager()
{
  logger = Logger::getLogger();

  m_pluginType = PLUGIN_TYPE_ID_OTHER;
}

/**
 * Update plugin info by merging the JSON plugin config over base plugin config
 *
 * @param    info			The plugin info structure
 * @param    json_plugin_name		JSON plugin name
 * @param    json_plugin_defaults	JSON plugin defaults dict
 * @param    json_plugin_description	JSON plugin description
 */
void updateJsonPluginConfig(PLUGIN_INFORMATION *info, string json_plugin_name, string json_plugin_defaults, string json_plugin_description)
{
	Logger *logger = Logger::getLogger();
	logger->debug("Loading base plugin for JSON plugin, so updating plugin_info structure loaded from base plugin");
	char *nameStr = new char [json_plugin_name.length()+1];
	std::strcpy (nameStr, json_plugin_name.c_str());
	info->name = nameStr;
	
	// Update json_plugin_description in plugin->description
	Document doc;
	doc.Parse(json_plugin_defaults.c_str());
	if (doc.HasParseError())
	{
		logger->error("Parse error in plugin '%s' defaults: %s at %d '%s'", json_plugin_name.c_str(),
					GetParseError_En(doc.GetParseError()), (unsigned)doc.GetErrorOffset(),
                        StringAround(json_plugin_defaults, (unsigned)doc.GetErrorOffset()));
		return;
	}

	Document docBase;
	docBase.Parse(info->config);
	if (docBase.HasParseError())
	{
		logger->error("Parse error in plugin '%s' information defaults: %s at %d '%s'", json_plugin_name.c_str(),
					GetParseError_En(doc.GetParseError()), (unsigned)doc.GetErrorOffset(),
                        			StringAround(info->config, (unsigned)doc.GetErrorOffset()));
		return;
	}

	static const char* kTypeNames[] = { "Null", "False", "True", "Object", "Array", "String", "Number" };

	DefaultConfigCategory basePluginCc("base", string(info->config));
	logger->debug("Original basePluginCc=%s", basePluginCc.toJSON().c_str());
		
	// Iterate over overlay config and find same item in base config and update their default from overlay to base config
	for (auto& m : doc.GetObject())
	{
		rapidjson::StringBuffer sb;
		rapidjson::Writer<rapidjson::StringBuffer> writer( sb );
		m.value.Accept( writer );
		string s = sb.GetString();
		//logger->debug("m.value.type()=%s, m.value.GetString()=%s", kTypeNames[m.value.GetType()], s.c_str());

		// find item with name 'm.name.GetString()' in base config
		if (!docBase.HasMember(m.name.GetString()))
		{
			logger->warn("Item with name '%s' missing from base config, ignoring it", m.name.GetString());
			continue;
		}
		else
		{
			string baseItemValue = basePluginCc.getDefault(m.name.GetString());
			//logger->debug("Original baseItemValue=%s", baseItemValue.c_str());
			
			Value::MemberIterator baseItemDefault = docBase[m.name.GetString()].FindMember("default");
			Value::MemberIterator overlayItemDefault = m.value.FindMember("default");
			if(baseItemDefault == docBase.MemberEnd() || overlayItemDefault == m.value.MemberEnd())
			{
				logger->warn("Default value for item with name %s missing from base config, ignoring it", m.name.GetString());
				continue;
			}
			else
			{
				//logger->debug("baseItemDefault: name=%s, type=%s, value=%s", 
				//		baseItemDefault->name.GetString(), kTypeNames[baseItemDefault->value.GetType()], baseItemDefault->value.GetString());
				string s;
				if (overlayItemDefault->value.IsObject())
				{
					rapidjson::StringBuffer sb;
					rapidjson::Writer<rapidjson::StringBuffer> writer( sb );
					overlayItemDefault->value.Accept( writer );
					s = sb.GetString();
				}
				else if (overlayItemDefault->value.IsString())
				{
					s = overlayItemDefault->value.GetString();
				}
				else if (overlayItemDefault->value.IsDouble())
				{
					s = to_string(overlayItemDefault->value.GetDouble());
				}
				else if (overlayItemDefault->value.IsNumber())
				{
					s = to_string(overlayItemDefault->value.GetInt());
				}
				else if (overlayItemDefault->value.IsBool())
				{
					s = overlayItemDefault->value.GetBool() ? "true" : "false";
				}
				else
				{
					logger->error("Unable to handle overlayItemDefault: name=%s, type=%d",
					overlayItemDefault->name.GetString(), overlayItemDefault->value.GetType());
				}
				//logger->debug("overlayItemDefault: name=%s, type=%s, value=%s",
				//	overlayItemDefault->name.GetString(), kTypeNames[overlayItemDefault->value.GetType()], s.c_str());
				
				basePluginCc.setDefault(m.name.GetString(), s);
				//logger->debug("Updated basePluginCc=%s", basePluginCc.toJSON().c_str());
				//logger->printLongString(basePluginCc.itemsToJSON());
			}
		}
	}
	
	// Update info->config
	char *confStr = new char [basePluginCc.itemsToJSON().length()+1];
	std::strcpy (confStr, basePluginCc.itemsToJSON().c_str());
	info->config = confStr;
	//logger->debug("\"defaults\" updated:");
	//logger->printLongString(info->config);

	// Update plugin name and description
	Document doc2;
	doc2.Parse(info->config);
	if (doc2.HasParseError())
	{
		logger->error("Parse error in information returned from plugin: %s at %d '%s'", 
					GetParseError_En(doc2.GetParseError()), (unsigned)doc2.GetErrorOffset(),
                        			StringAround(info->config, (unsigned)doc2.GetErrorOffset()));
	}
	if (doc2.HasMember("plugin"))
	{
		Value::MemberIterator itemValueIter = doc2["plugin"].FindMember("default");
		//logger->debug("plugin->default=%s", itemValueIter->value.GetString());
		itemValueIter->value.SetString(json_plugin_name.c_str(), doc2.GetAllocator());

		Value::MemberIterator itemValueIter2 = doc2["plugin"].FindMember("description");
		//logger->debug("plugin->description=%s", itemValueIter2->value.GetString());
		itemValueIter2->value.SetString(json_plugin_description.c_str(), doc2.GetAllocator());
	}
	StringBuffer buf;
	Writer<StringBuffer> writer (buf);
	doc2.Accept (writer);
	char *confStr2 = new char [string(buf.GetString()).length()+1];
	std::strcpy (confStr2, buf.GetString());
	info->config = confStr2;
	delete[] confStr;
	logger->debug("Fields updated based on JSON config overlay:");
	logger->printLongString(info->config);
}

/**
 * Find a specific plugin in the directories listed in FLEDGE_PLUGIN_PATH
 *
 * @param    name		The plugin name
 * @param    _type		The plugin type string
 * @param    _plugin_path	Value of FLEDGE_PLUGIN_PATH environment variable
 * @param    type		The plugin type
 * @return   string		The absolute path of plugin
 */
string PluginManager::findPlugin(string name, string _type, string _plugin_path, PLUGIN_TYPE type)
{
	if (type != BINARY_PLUGIN && type != PYTHON_PLUGIN && type != JSON_PLUGIN)
	{
		return "";
	}
	
	stringstream plugin_path(_plugin_path);
	string temp;
	
	// Tokenizing w.r.t. semicolon ';' 
	while(getline(plugin_path, temp, ';')) 
	{
		string path = temp+"/"+_type+"/"+name+"/";
		switch(type)
		{
			case BINARY_PLUGIN:
				path += "lib"+name+".so";
				break;
			case PYTHON_PLUGIN:
				path += name+".py";
				break;
			case JSON_PLUGIN:
				path += name+".json";
				break;
		}
		if (access(path.c_str(), F_OK) == 0)
		{
			Logger::getLogger()->debug("Found plugin @ %s", path.c_str());
			return path;
		}
	}
	Logger::getLogger()->debug("Didn't find plugin : name=%s, _type=%s, _plugin_path=%s", name.c_str(), _type.c_str(), _plugin_path.c_str());
	return "";
}

/**
 * Set Plugin Type
 */
void PluginManager::setPluginType(tPluginType type)
{
	m_pluginType = type;
}

/**
 * Load a given plugin
 */
PLUGIN_HANDLE PluginManager::loadPlugin(const string& _name, const string& type)
{
PluginHandle *pluginHandle = NULL;
PLUGIN_HANDLE hndl;
char		buf[MAXPATHLEN];

	string json_plugin_name, json_base_plugin_name, json_plugin_defaults, json_plugin_description;
	bool json_plugin = false;
	string name(_name);

	if (pluginNames.find(name) != pluginNames.end())
	{
		if (type.compare(pluginTypes.find(name)->second))
		{
			logger->error("Plugin %s is already loaded but not the expected type %s\n",
					name.c_str(), type.c_str());
			return NULL;
		}
		return pluginNames[name];
	}

	const char *home = getenv("FLEDGE_ROOT");
	const char *plugin_path = getenv("FLEDGE_PLUGIN_PATH");
	string paths("");
	if (home)
	{
		paths += string(home)+"/plugins";
		paths += ";"+string(home)+"/python/fledge/plugins";
	}
	if (plugin_path)
		paths += (home ? ";" : "")+string(plugin_path);
  
	/*
	 * Find and try to load the plugin that is described via a JSON file
	 */
	string path = findPlugin(name, type, paths, JSON_PLUGIN);
	strncpy(buf, path.c_str(), sizeof(buf));
	if (buf[0] && access(buf, F_OK|R_OK) == 0)
	{
		// read config from JSON file
		ifstream ifs(buf, ios::in);
	
		std::stringstream sstr;
		sstr << ifs.rdbuf();
		string json=sstr.str();
		json.erase(remove(json.begin(), json.end(), '\t'), json.end());
		json.erase(remove(json.begin(), json.end(), '\n'), json.end());
	
		// parse JSON document
		Document doc;
		doc.Parse(json.c_str());
		if (doc.HasParseError())
		{
			Logger::getLogger()->error("Parse error for JSON plugin config in '%s': %s at %d", name.c_str(),
					GetParseError_En(doc.GetParseError()), (unsigned)doc.GetErrorOffset());
			return NULL;
		}
		
		if (!(doc.HasMember("name") && doc["name"].IsString() &&
			doc.HasMember("defaults") && doc["defaults"].IsObject() &&
			doc.HasMember("connection") && doc["connection"].IsString()))
		{
			Logger::getLogger()->error("JSON config for plugin @ '%s' is missing/misconfigured, exiting...", buf);
			return NULL;
		}
	
		json_plugin_name = doc["name"].GetString();
		json_base_plugin_name = doc["connection"].GetString();
	
		if (doc.HasMember("description") && doc["description"].IsString())
		{
			json_plugin_description = doc["description"].GetString();
		}
		if (doc["defaults"].IsObject())
		{
			rapidjson::StringBuffer sb;
			rapidjson::Writer<rapidjson::StringBuffer> writer( sb );
			doc["defaults"].Accept( writer );
			json_plugin_defaults = sb.GetString();
		}
	
		// set plugin name so that base plugin can be loaded next
		json_plugin = true;
		name = json_base_plugin_name;
		logger->debug("json_plugin=%s, json_plugin_name=%s, json_base_plugin_name=%s, json_plugin_description=%s, json_plugin_defaults=%s", 
			json_plugin?"true":"false", json_plugin_name.c_str(), json_base_plugin_name.c_str(), json_plugin_description.c_str(), json_plugin_defaults.c_str());
	}
  
	/*
	 * Find and try to load the dynamic library that is the plugin
	 */
	path = findPlugin(name, type, paths, BINARY_PLUGIN);
	strncpy(buf, path.c_str(), sizeof(buf));
	if (buf[0] && access(buf, F_OK|R_OK) == 0)
	{
		if (m_pluginType == PLUGIN_TYPE_ID_STORAGE)
		{
			pluginHandle = new BinaryPluginHandle(name.c_str(), buf, PLUGIN_TYPE_ID_STORAGE);
		}
		else
		{
			pluginHandle = new BinaryPluginHandle(name.c_str(), buf);
		}

		hndl = pluginHandle->getHandle();
		if (hndl != NULL)
		{
			func_t infoEntry = (func_t)pluginHandle->GetInfo();
			if (infoEntry == NULL)
			{
				// Unable to find plugin_info entry point
				logger->error("C plugin %s does not support plugin_info entry point.\n", name.c_str());
				delete pluginHandle;
				return NULL;
			}
			PLUGIN_INFORMATION *info = (PLUGIN_INFORMATION *)(*infoEntry)();

			logger->debug("%s:%d: name=%s, type=%s, default config=%s", __FUNCTION__, __LINE__, info->name, info->type, info->config);
	  
			if (strcmp(info->type, type.c_str()) != 0)
			{
				// Log error, incorrect plugin type
				logger->error("C plugin %s is not of the expected type %s, it is of type %s.\n",
							name.c_str(), type.c_str(), info->type);
				delete pluginHandle;
				return NULL;
			}

			if (json_plugin)
			{
				updateJsonPluginConfig(info, json_plugin_name, json_plugin_defaults, json_plugin_description);
			}
	  
			plugins.push_back(pluginHandle);
			pluginNames[name] = hndl;
			pluginTypes[name] = type;
			pluginImplTypes[hndl] = BINARY_PLUGIN;
			pluginInfo[hndl] = info;

			pluginHandleMap[hndl] = pluginHandle;
			logger->debug("%s:%d: Added entry in pluginHandleMap={%p, %p}", __FUNCTION__, __LINE__, hndl, pluginHandle);
		}
		else
		{
			logger->error("PluginManager: Failed to load C plugin %s in %s: %s.",
				name.c_str(), buf, dlerror());
		}
		return hndl;
	}

	// look for and load python plugin with given name
	path = findPlugin(name, type, paths, PYTHON_PLUGIN);
	strncpy(buf, path.c_str(), sizeof(buf));
	if (buf[0] && access(buf, F_OK|R_OK) == 0)
	{
		// is it Notification Rule Python plugin ?
		if (type.compare(PLUGIN_TYPE_NOTIFICATION_RULE) == 0 ||
			type.compare(PLUGIN_TYPE_NOTIFICATION_DELIVERY) == 0)
		{
			pluginHandle = new NotificationPythonPluginHandle(name.c_str(), buf);
		}
		else if (type.compare(PLUGIN_TYPE_FILTER) == 0)
		{
			pluginHandle = new FilterPythonPluginHandle(name.c_str(), buf);
		}
		else if (type.compare(PLUGIN_TYPE_NORTH) == 0)
		{
			pluginHandle = new NorthPythonPluginHandle(name.c_str(), buf);
		}
		else
		{
			pluginHandle = new SouthPythonPluginHandle(name.c_str(), buf);
		}

		hndl = pluginHandle->getHandle();

		if (hndl != NULL)
		{
			func_t infoEntry = (func_t)pluginHandle->GetInfo();
			if (infoEntry == NULL)
			{
				// Unable to find plugin_info entry point
				logger->error("Python plugin %s does not support plugin_info entry point.\n", name.c_str());
				delete pluginHandle;
				return NULL;
			}
			PLUGIN_INFORMATION *info = (PLUGIN_INFORMATION *)(*infoEntry)();
			if (!info)
			{
				// Unable to get data from plugin_info entry point
				logger->error("Python plugin %s cannot get data from plugin_info entry point.\n", name.c_str());
				delete pluginHandle;
				return NULL;
			}
	 
			if (strcmp(info->type, type.c_str()) != 0)
			{
				// Log error, incorrect plugin type
				logger->error("C plugin %s is not of the expected type %s, it is of type %s.\n",
						name.c_str(),
						type.c_str(),
						info->type);
				delete pluginHandle;
				return NULL;
			}
			if (json_plugin)
			{
				updateJsonPluginConfig(info,
							json_plugin_name,
							json_plugin_defaults,
							json_plugin_description);
			}
	 
			plugins.push_back(pluginHandle);
			pluginNames[name] = hndl;
			pluginTypes[name] = type;
			pluginImplTypes[hndl] = PYTHON_PLUGIN;
			pluginInfo[hndl] = info;
			pluginHandleMap[hndl] = pluginHandle;
		}
		else
		{
			logger->error("PluginManager: Failed to load python plugin %s in %s",
					name.c_str(),
					buf);
		}
		return hndl;
  	}
  
	if (json_plugin) // if base plugin had been found, this function would have returned already
	{
	  	logger->error("PluginManager: Could not load base plugin '%s' for JSON plugin '%s'", json_base_plugin_name.c_str(), json_plugin_name.c_str());
		return NULL;
	}
  
	logger->error("PluginManager: Failed to load plugin '%s' as any of the recognised types. Check that the plugin exists and the plugin name and installation directory match", name.c_str());
	return NULL;
}

/**
 * Find a loaded plugin by name.
 */
PLUGIN_HANDLE PluginManager::findPluginByName(const string& name)
{
  if (pluginNames.find(name) == pluginNames.end())
  {
    return NULL;
  }
  return pluginNames.find(name)->second;
}

/**
 * Find a loaded plugin by type
 */
PLUGIN_HANDLE PluginManager::findPluginByType(const string& type)
{
  if (pluginNames.find(type) == pluginNames.end())
  {
    return NULL;
  }
  return pluginNames.find(type)->second;
}

/**
 * Return the information for a named plugin
 */
PLUGIN_INFORMATION *PluginManager::getInfo(const PLUGIN_HANDLE handle)
{
  if (pluginInfo.find(handle) == pluginInfo.end())
  {
    return NULL;
  }
  return pluginInfo.find(handle)->second;
}

/**
 * Resolve a symbol within the plugin
 */
PLUGIN_HANDLE PluginManager::resolveSymbol(PLUGIN_HANDLE handle, const string& symbol)
{
  if (pluginHandleMap.find(handle) == pluginHandleMap.end())
  {
  	logger->warn("%s:%d: Cannot find PLUGIN_HANDLE in pluginHandleMap: returning NULL", __FUNCTION__, __LINE__);
    return NULL;
  }
  return pluginHandleMap.find(handle)->second->ResolveSymbol(symbol.c_str());
}

/**
 * Get the installed plugins in the given plugin type
 * subdirectory of "plugins" under FLEDGE_ROOT
 * Plugin type is one of:
 * south, north, filter, notificationRule, notificationDelivery
 *
 * @param    type		The plugin type
 * @param    plugins		The output plugin list name to fill	
 */
void PluginManager::getInstalledPlugins(const string& type,
					list<string>& plugins)
{
	char *home = getenv("FLEDGE_ROOT");
	char *plugin_path = getenv("FLEDGE_PLUGIN_PATH");
	string paths("");
	if (home)
	{
		// Binary C plugins
		paths += string(home)+"/plugins";

		// Python Plugins
		paths += ";"+string(home)+"/python/fledge/plugins";
	}
	if (plugin_path)
	{
		paths += (home?";":"")+string(plugin_path);
	}

	stringstream _paths(paths);
	
	string temp;
	// Tokenize w.r.t. semicolon ';'
	while(getline(_paths, temp, ';'))
	{
		struct dirent *entry;
		DIR *dp;
		string path = temp + "/" + type + "/";

		// Open the plugins dir/type
		dp = opendir(path.c_str());

		if (!dp)
		{
			// Can not open specified dir path
			char msg[128];
			char* ret = strerror_r(errno, msg, 128);
			logger->warn("Can not access plugin directory %s: %s",
				      path.c_str(),
				      ret);
			continue;
		}

		/**
		 * Get all sub directory names in path:
		 * path = plugins/filter/
		 *     delta
		 *     scale

		 * Plugin filename is libdelta.so, libscale.so
		 * Plugin name is the subdirecory name in path
		 * Skip directory starting with '_' or 
		 * with name 'common'
		 */
		while ((entry = readdir(dp)))
		{
			if (strcmp (entry->d_name, "..") != 0 &&
			    strcmp (entry->d_name, ".") != 0 && 
				strcmp (entry->d_name, "common") != 0 &&
				entry->d_name[0] != '_')
			{
				struct stat stbuf;
				bool is_dir(false);
				if (stat((path + entry->d_name).c_str(), &stbuf) != 0) {
					continue;
				}
				is_dir = S_ISDIR(stbuf.st_mode);
				if (!is_dir) {
					continue;
				}

				/* check for duplicate names to avoid
					multiple loadPlugin calls
				*/ 
				bool is_duplicate = false;
				for (const auto& loadedPlugin : plugins)
				{
					if (loadedPlugin == entry->d_name)
					{
						is_duplicate = true;
						break;
					}
				}
				if (!is_duplicate) 
				{
					// Load plugin, given its name: the directory name
					loadPlugin(entry->d_name, type);
					// Add name to ouput list
					plugins.push_back(entry->d_name);
				}
			}
		}
		closedir(dp);
	}
}

/**
 * Return a list of plugins matching the criteria
 * of plugin type and plugin flags
 *
 * @param type          The plugin type to match
 * @param flags         A bitmask of flags to match
 * @return vector<string>       A list of matching plugin names
 */
std::vector<string> PluginManager::getPluginsByFlags(const std::string& type, 
									unsigned int flags) 
{
	// Plugins matching type and flag bits
	std::vector<std::string> matchingPlugins;
	
	// Get list of installed plugins of given type
	std::list<std::string> plugins;
	getInstalledPlugins(type, plugins);
	
	/* Iterate list of installed plugins and
		match plugin 'options' with passed 
		plugin flags
	*/
	for (auto &pName: plugins) 
	{
		// Fetch loaded plugin handle
		auto pluginHandle = pluginNames.find(pName);
		unsigned int pluginOptions = 0;
		if (pluginHandle != pluginNames.end()) {
			pluginOptions = getInfo(pluginHandle->second)->options;
		}
		// Match bit fields corresponding to loaded plugins
		if ((flags & pluginOptions) == flags) {
			matchingPlugins.push_back(pName);
		}
	}
	
	return matchingPlugins;
}
