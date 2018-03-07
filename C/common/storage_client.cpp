/*
 * FogLAMP storage service client
 *
 * Copyright (c) 2018 OSIsoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <storage_client.h>
#include <reading.h>
#include <rapidjson/document.h>
#include <rapidjson/error/en.h>
#include <service_record.h>
#include <string>
#include <sstream>
#include <iostream>

using namespace std;
using namespace rapidjson;
using HttpClient = SimpleWeb::Client<SimpleWeb::HTTP>;


/**
 * Storage Client constructor
 */
StorageClient::StorageClient(const string& hostname, const unsigned short port)
{
ostringstream urlbase;

	m_logger = Logger::getLogger();
	urlbase << hostname << ":" << port;
	m_client = new HttpClient(urlbase.str());
}

/**
 * Destructor for storage client
 */
StorageClient::~StorageClient()
{
	delete m_client;
}

/**
 * Append a single reading
 */
bool StorageClient::readingAppend(Reading& reading)
{
	try {
		ostringstream convert;

		convert << "{ \"readings\" : [ ";
		convert << reading.toJSON();
		convert << " ] }";
		auto res = m_client->request("POST", "/storage/reading", convert.str());
		if (res->status_code.compare("200 OK") == 0)
		{
			return true;
		}
		Document doc;
		doc.Parse(res->content.string().c_str());
		if (doc.HasParseError())
		{
			m_logger->info("POST readings result %s.", res->status_code.c_str());
			m_logger->error("Failed to parse result of readingAppend. %s",
					GetParseError_En(doc.GetParseError()));
		}
		else if (doc.HasMember("message"))
		{
			m_logger->error("Failed to append readings: %s",
				doc["message"].GetString());
		}
		return false;
	} catch (exception& ex) {
		m_logger->error("Failed to append reading: %s", ex.what());
	}
	return false;
}

/**
 * Append multiple readings
 */
bool StorageClient::readingAppend(const vector<Reading *>& readings)
{
	try {
		ostringstream convert;

		convert << "{ \"readings\" : [ ";
		for (vector<Reading *>::const_iterator it = readings.cbegin();
						 it != readings.cend(); ++it)
		{
			if (it != readings.cbegin())
			{
				convert << ", ";
			}
			convert << (*it)->toJSON();
		}
		convert << " ] }";
		auto res = m_client->request("POST", "/storage/reading", convert.str());
		if (res->status_code.compare("200 OK") == 0)
		{
			return true;
		}
		ostringstream resultPayload;
		resultPayload << res->content.rdbuf();
		Document doc;
		doc.Parse(resultPayload.str().c_str());
		if (doc.HasParseError())
		{
			m_logger->info("POST readings result %s.", res->status_code.c_str());
			m_logger->error("Failed to parse result of readingAppend. %s",
					GetParseError_En(doc.GetParseError()));
			m_logger->error("Unparsable response payload is: %s.", resultPayload.str().c_str());
		}
		else if (doc.HasMember("message"))
		{
			m_logger->info("POST readings result %s", res->status_code.c_str());
			m_logger->error("Failed to append readings: %s",
				doc["message"].GetString());
		}
		return false;
	} catch (exception& ex) {
		m_logger->error("Failed to append reading: %s", ex.what());
	}
	return false;
}
