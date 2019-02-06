/*
 * FogLAMP persist plugin data class.
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Massimiliano Pinto
 */

#include "rapidjson/writer.h"
#include "rapidjson/stringbuffer.h"
#include <resultset.h>
#include <where.h>
#include <plugin_data.h>

using namespace std;
using namespace rapidjson;

/**
 * PluginData constructor
 * @param client	StorageClient pointer
 */
PluginData::PluginData(StorageClient* client) : m_storage(client)
{
}

/**
 * Load stored data for a given key.
 *
 * @param    key	Given key for data load
 * @return   JSON string with found data or empty JSON data
 */
string PluginData::loadStoredData(const string& key)
{
	// Set empty JSON dcocument
	string foundData("{}");
	const Condition conditionId(Equals);
	Where* wKey = new Where("key",
				conditionId,
				key);

	ResultSet* pluginData = m_storage->queryTable("plugin_data", wKey);
	if (pluginData != NULL && pluginData->rowCount())
	{
		// Get the first row only
		ResultSet::RowIterator it = pluginData->firstRow();
		// Access the element
		ResultSet::Row* row = *it;
		if (row)
		{
			// Get column value
			ResultSet::ColumnValue* theVal = row->getColumn("data");
			// get column type
			ColumnType type  = row->getType("data");
			if (type == JSON_COLUMN)
			{
				// Convert JSON object to string
                        	const rapidjson::Value* val = theVal->getJSON();
				rapidjson::StringBuffer strbuf;
				rapidjson::Writer<rapidjson::StringBuffer> writer(strbuf);
				val->Accept(writer);
				foundData = strbuf.GetString();
			}
			else if (type == STRING_COLUMN)
			{
				// just a string
				foundData = theVal->getString();
			}
			else
			{
				// Other column types are not supported
			}
		}
	}

	// Free resultset
	delete pluginData;

	// Return found data
	return foundData;
}

/**
 * Store plugin data for a given key.
 *
 * @param    key	The given key
 * @param    data	The JSON data to save (as string)
 * @return		true on success, false otherwise. 
 */
bool PluginData::persistPluginData(const string& key,
				   const string& data)
{
	Document JSONData;
	JSONData.Parse(data.c_str());
	if (JSONData.HasParseError())
	{
		return false;
	}	

	bool ret = true;

	// Prepare WHERE key = 
	const Condition conditionUpdate(Equals);
	Where wKey("key",
		   conditionUpdate,
		   key);
	InsertValues updateData;
	updateData.push_back(InsertValue("data", JSONData));

	// Try update first
	if (m_storage->updateTable("plugin_data",
				   updateData,
				   wKey) == -1)
	{
		// Update filure: try insert
		InsertValues insertData;
		insertData.push_back(InsertValue("key", key));
		insertData.push_back(InsertValue("data", JSONData));

		if (m_storage->insertTable("plugin_data",
					   insertData) == -1)
		{
			ret = false;
		}
	}

	return ret;
}
