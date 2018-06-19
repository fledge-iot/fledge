/*
 * FogLAMP storage service client
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <purge_result.h>
#include <string>
#include <rapidjson/document.h>
#include <sstream>

using namespace std;
using namespace rapidjson;

/**
 * Construct a purge result from a JSON document returned from
 * the FogLAMP storage service.
 */
PurgeResult::PurgeResult(const std::string& json)
{
	Document doc;
	doc.Parse(json.c_str());
	if (doc.HasParseError())
	{
		throw new exception();
	}
	if (doc.HasMember("removed"))
	{
		m_removed = doc["removed"].GetUint();
	}
	else
	{
		m_removed = 0;
	}
	if (doc.HasMember("unsentPurged"))
	{
		m_unsentPurged = doc["unsentPurged"].GetUint();
	}
	else
	{
		m_unsentPurged = 0;
	}
	if (doc.HasMember("unsentRetained"))
	{
		m_unsentRetained = doc["unsentRetained"].GetUint();
	}
	else
	{
		m_unsentRetained = 0;
	}
	if (doc.HasMember("readings"))
	{
		m_remaining = doc["readings"].GetUint();
	}
	else
	{
		m_remaining = 0;
	}
}
