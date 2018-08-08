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

void
ThingSpeak::connect()
{
	/**
	 * Extract host, port, path from URL
	 */
	size_t findProtocol = m_url.find_first_of(":");
	string protocol = m_url.substr(0,findProtocol);

	string tmpUrl = m_url.substr(findProtocol + 3);
	size_t findPort = tmpUrl.find_first_of(":");
	string hostName = tmpUrl.substr(0, findPort);

	size_t findPath = tmpUrl.find_first_of("/");
	string port = tmpUrl.substr(findPort + 1 , findPath - findPort -1);
	string path = tmpUrl.substr(findPath);

	/**
	 * Allocate the HTTPS handler for "Hostname : port"
	 */
	string hostAndPort(hostName + ":" + port);
	m_https  = new SimpleHttps(hostAndPort);
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
	for (auto it = readings.cbegin(); it != readings.cend(); ++it)
	{
		if (it != readings.cbegin())
		{
			payload << ",";
		}
		payload << "{ \"created_at\": \"";
		payload << (*it)->getAssetDateTime() << "\",";
		vector<Datapoint *> datapoints = (*it)->getReadingData();
		for (auto dit = datapoints.cbegin(); dit != datapoints.cend();
					++dit)
		{
			if (dit != datapoints.cbegin())
			{
				payload << ",";
			}
			payload << (*dit)->toJSONProperty();
		}
		payload << "}";
	}

	char url[100];
	snprintf(url, sizeof(url), "%s/%d/bulk_update.json", m_url.c_str(),
			m_channel);

	int errorCode;
	if ((errorCode = m_https->sendRequest("POST", url, m_headers, payload.str())) == 200)
	{
		return readings.size();
	}
	else
	{

		Logger::getLogger()->error("Failed to send to ThingSpeak %s, errorCode %d", url, errorCode);
		return 0;
	}
}
