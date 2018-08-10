/*
 * FogLAMP ThingSpeak north plugin.
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <thingspeak.h>
#include <logger.h>

using namespace	std;

ThingSpeak::ThingSpeak(const string& url, const int channel, const string& apiKey) :
	m_url(url), m_channel(channel), m_apiKey(apiKey), m_https(0)
{
	m_headers.push_back(pair<string, string>("Content-Type", "application/json"));
}

ThingSpeak::~ThingSpeak()
{
	if (m_https)
	{
		delete m_https;
	}
}

/**
 * Add an asset and datapoint to send as a ThingSpeak field
 *
 * @param asset	The asset name to select
 * @param datapoint	The datapoint within the asset
 */
bool
ThingSpeak::addField(const string& asset, const string& datapoint)
{
	m_fields.push_back(pair<string, string>(asset, datapoint));
	return true;
}

/**
 * Create the HTTPS connection to the ThingSpeak API
 */
void
ThingSpeak::connect()
{
	/**
	 * Extract host and port from URL
	 */
	size_t findProtocol = m_url.find_first_of(":");
	string protocol = m_url.substr(0,findProtocol);

	string tmpUrl = m_url.substr(findProtocol + 3);
	size_t findPort = tmpUrl.find_first_of(":");
	size_t findPath = tmpUrl.find_first_of("/");
	string port, hostName;
	if (findPort == string::npos)
	{
		hostName = tmpUrl.substr(0, findPath);
		m_https  = new SimpleHttps(hostName);
	}
	else
	{
		hostName = tmpUrl.substr(0, findPort);
		port = tmpUrl.substr(findPort + 1 , findPath - findPort -1);
		string hostAndPort(hostName + ":" + port);
		m_https  = new SimpleHttps(hostAndPort);
	}
}

/**
 * Send the readings to the ThingSpeak channel
 *
 * @param readings	The Readings to send
 * @return	The number of readings sent
 */
uint32_t
ThingSpeak::send(const vector<Reading *> readings)
{
ostringstream	payload;

	payload << "{ ";
	payload << "\"write_api_key\":\"" << m_apiKey << "\",";
	payload << "\"updates\":[";
	bool	first = true;
	for (auto it = readings.cbegin(); it != readings.cend(); ++it)
	{
		string assetName = (*it)->getAssetName();
		bool found = false;
		int fieldIdx;
		// First do a pass and see if any data points of this asset are included
		for (fieldIdx = 0; fieldIdx < m_fields.size(); fieldIdx++)
		{
			if (m_fields[fieldIdx].first.compare(assetName) == 0)
			{
				found = true;
				break;
			}
		}
		if (!found)
		{
			continue;
		}
		/*
		 * At least one of the readings datapoints are required
		 * from this reading, now traverse the readings and extract
		 * the datapoints that are required.
		 *
		 * We output the date once for all the datapoints that are
		 * valid and then output each of the fields.
		 */
		bool outputDate = false;
		vector<Datapoint *> datapoints = (*it)->getReadingData();
		for (auto dit = datapoints.cbegin(); dit != datapoints.cend();
					++dit)
		{
			string name = (*dit)->getName();
			for (int fieldIdx = 0; fieldIdx < m_fields.size(); fieldIdx++)
			{
				if (m_fields[fieldIdx].first.compare(assetName) == 0 &&
					m_fields[fieldIdx].second.compare(name) == 0)
				{
					if (outputDate == false)
					{
						if (first == false)
						{
							payload << ",";
						}
						first = false;
						outputDate = true;
						payload << "{ \"created_at\": \"";
						payload << (*it)->getAssetDateTime(Reading::FMT_ISO8601) << "\",";
					}
					else
					{
						payload << ",";
					}
					payload << "\"field" << fieldIdx + 1;
					payload << "\" : " << (*dit)->getData().toString();
				}
			}
		}
		if (outputDate == true)
		{
			payload << "}";
		}
	}
	payload << "]}";

	char url[100];
	snprintf(url, sizeof(url), "%s/%d/bulk_update.json", m_url.c_str(),
			m_channel);

	int errorCode;
	if ((errorCode = m_https->sendRequest("POST", url, m_headers, payload.str())) == 200 || errorCode == 202)
	{
		return readings.size();
	}
	else
	{

		Logger::getLogger()->error("Failed to send to ThingSpeak %s, errorCode %d", url, errorCode);
		return 0;
	}
}
