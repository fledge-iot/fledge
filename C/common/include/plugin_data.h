#ifndef _PLUGIN_DATA_H
#define _PLUGIN_DATA_H
/*
 * FogLAMP persist plugin data class.
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Massimiliano Pinto
 */

#include <storage_client.h>

class PluginData
{

public:
	PluginData(StorageClient* client);
	~PluginData() {};
	// Load data
	std::string loadStoredData(const std::string& key);
	// Store data
	bool persistPluginData(const std::string& key,
			       const std::string& data);

private:
	StorageClient*		m_storage;
};

#endif
