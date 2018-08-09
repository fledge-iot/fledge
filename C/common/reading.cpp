/*
 * FogLAMP storage service client
 *
 * Copyright (c) 2018 OSIsoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch, Massimiliano Pinto
 */
#include <reading.h>
#include <ctime>
#include <string>
#include <sstream>
#include <iostream>
#include <uuid/uuid.h>

using namespace std;

/**
 * Reading constructor
 *
 * A reading is a container for the values related to a single asset.
 * Each actual datavalue that relates to that asset is held within an
 * instance of a Datapoint class.
 */
Reading::Reading(const string& asset, Datapoint *value) : m_asset(asset)
{
uuid_t	uuid;
char	uuid_str[37];

	m_values.push_back(value);
	uuid_generate_time_safe(uuid);
	uuid_unparse_lower(uuid, uuid_str);
	m_uuid = string(uuid_str);
	// Store seconds and microseconds
	gettimeofday(&m_timestamp, NULL);
}

/**
 * Reading constructor
 *
 * A reading is a container for the values related to a single asset.
 * Each actual datavalue that relates to that asset is held within an
 * instance of a Datapoint class.
 */
Reading::Reading(const string& asset, vector<Datapoint *> values) : m_asset(asset)
{
uuid_t	uuid;
char	uuid_str[37];

	for (auto it = values.cbegin(); it != values.cend(); it++)
	{
		m_values.push_back(*it);
	}
	uuid_generate_time_safe(uuid);
	uuid_unparse_lower(uuid, uuid_str);
	m_uuid = string(uuid_str);
	// Store seconds and microseconds
	gettimeofday(&m_timestamp, NULL);
}

/**
 * Reading copy constructor
 */
Reading::Reading(const Reading& orig) : m_asset(orig.m_asset),
	m_timestamp(orig.m_timestamp), m_uuid(orig.m_uuid)
{
	for (auto it = orig.m_values.cbegin(); it != orig.m_values.cend(); it++)
	{
		m_values.push_back(new Datapoint(**it));
	}
}

/**
 * Destructor for Reading class
 */
Reading::~Reading()
{
	for (auto it = m_values.cbegin(); it != m_values.cend(); it++)
	{
		delete(*it);
	}
}

/**
 * Add another data point to an asset reading
 */
void Reading::addDatapoint(Datapoint *value)
{
	m_values.push_back(value);
}

/**
 * Return the asset reading as a JSON structure encoded in a
 * C++ string.
 */
string Reading::toJSON() const
{
ostringstream convert;

	convert << "{ \"asset_code\" : \"";
	convert << m_asset;
	convert << "\", \"read_key\" : \"";
	convert << m_uuid;
	convert << "\", \"user_ts\" : \"";

	// Add date_time with microseconds + timezone UTC:
	// YYYY-MM-DD HH24:MM:SS.MS+00:00
	convert << Reading::getAssetDateTime(FMT_DEFAULT) << "+00:00";

	// Add values
	convert << "\", \"reading\" : { ";
	for (auto it = m_values.cbegin(); it != m_values.cend(); it++)
	{
		if (it != m_values.cbegin())
		{
			convert << ", ";
		}
		convert << (*it)->toJSONProperty();
	}
	convert << " } }";

	return convert.str();
}

/**
 * Return a formatted m_timestamp DataTime
 * @param dateFormat    Format: FMT_DEFAULT or FMT_STANDARD
 * @return              The formatted datetime string
 */
const string Reading::getAssetDateTime(readingTimeFormat dateFormat) const
{
char date_time[DATE_TIME_BUFFER_LEN];
char micro_s[10];
ostringstream assetTime;

        // Populate tm structure
        const struct tm *timeinfo = std::localtime(&(m_timestamp.tv_sec));

        /**
         * Build date_time with format YYYY-MM-DD HH24:MM:SS.MS+00:00
         * this is same as Python3:
         * datetime.datetime.now(tz=datetime.timezone.utc)
         */

        // Create datetime with seconds
        std::strftime(date_time, sizeof(date_time),
		      m_dateTypes[dateFormat].c_str(),
                      timeinfo);

        // Add microseconds
        snprintf(micro_s,
                 sizeof(micro_s),
                 ".%06lu",
                 m_timestamp.tv_usec);

        // Add date_time + microseconds
        assetTime << date_time << micro_s;

	return assetTime.str();
}
