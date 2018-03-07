#ifndef _STORAGE_CLIENT_H
#define _STORAGE_CLIENT_H
/*
 * FogLAMP storage client.
 *
 * Copyright (c) 2018 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <client_http.hpp>
#include <reading.h>
#include <logger.h>
#include <string>
#include <vector>

using HttpClient = SimpleWeb::Client<SimpleWeb::HTTP>;

/**
 * Client for accessing the storage service
 */
class StorageClient {
	public:
		StorageClient(const std::string& hostname, const unsigned short port);
		~StorageClient();
		bool readingAppend(Reading& reading);
		bool readingAppend(const std::vector<Reading *> & readings);
	private:
		HttpClient		*m_client;
		Logger			*m_logger;
};
#endif

