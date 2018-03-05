/*
 * FogLAMP storage service client
 *
 * Copyright (c) 2018 OSIsoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <reading.h>
#include <ctime>
#include <string>
#include <sstream>
#include <iostream>
#include <uuid/uuid.h>

using namespace std;


/**
 * Storage Client constructor
 */
Reading::Reading(const string& asset, Datapoint *value) : m_asset(asset),
	m_timestamp(time(nullptr))
{
uuid_t	uuid;
char	uuid_str[37];

	m_values.push_back(value);
	uuid_generate_time_safe(uuid);
	uuid_unparse_lower(uuid, uuid_str);
	m_uuid = string(uuid_str);
}


/**
 * Destructor for storage client
 */
Reading::~Reading()
{
	for (auto it = m_values.cbegin(); it != m_values.cend(); it++)
	{
		delete(*it);
	}
}

void Reading::addDatapoint(Datapoint *value)
{
	m_values.push_back(value);
}

string Reading::toJSON()
{
ostringstream convert;

	convert << "{ \"asset_code\" : \"";
	convert << m_asset;
	convert << "\", \"read_key\" : \"";
	convert << m_uuid;
	convert << "\", \"user_ts\" : \"";
	convert << std::asctime(std::localtime(&m_timestamp));
	convert << "\", \"reading\" : { ";
	for (auto it = m_values.cbegin(); it != m_values.cend(); it++)
	{
		if (it != m_values.cbegin())
		{
			convert << ", ";
		}
		convert << (*it)->toJSONProperty();
	}
	convert << "} }";

	return convert.str();
}
