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

bool StorageClient::readingAppend(Reading& reading)
{
	try {
		auto res = m_client->request("POST", "/storage/reading", reading.toJSON());
	} catch (exception ex) {
	}
	return false;
}
