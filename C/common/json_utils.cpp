/*
 * FogLAMP utilities functions for handling JSON document
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Stefano Simonelli
 */

#include <iostream>
#include <string>
#include <vector>
#include "json_utils.h"
#include "rapidjson/document.h"

using namespace std;
using namespace rapidjson;

/**
 * Processes a string containing an array in JSON format and loads a vector of string
 *
 * @param vectorString  vector of string used by reference in which the JSON array will be loaded
 * @param JSONString    string containing an array in JSON format
 * @param Key           key of the JSON from which the array should be evaluated
 *
 */
bool JSONStringToVectorString(std::vector<std::string>& vectorString,
			      const std::string& JSONString,
			      const std::string& Key)
{
	bool success = true;

	Document JSONdoc;

	JSONdoc.Parse(JSONString.c_str());


	if (JSONdoc.HasParseError())
	{
		success = false;

	} else if (!JSONdoc.HasMember(Key.c_str()))
	{
		success = false;

	} else if (!JSONdoc[Key.c_str()].IsArray())
	{

		success = false;
	}

	if (success)
	{
		const Value &filterList = JSONdoc[Key.c_str()];
		if (!filterList.Size())
		{
			success = false;
		} else
		{
			for (Value::ConstValueIterator itr = filterList.Begin();
			     itr != filterList.End(); ++itr)
			{
				vectorString.emplace_back(itr->GetString());
			}

		}
	}

	return success;
}
