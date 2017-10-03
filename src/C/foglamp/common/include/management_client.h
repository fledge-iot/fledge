#ifndef _MANAGEMENT_CLIENT_H
#define _MANAGEMENT_CLIENT_H
/*
 * FogLAMP storage service.
 *
 * Copyright (c) 2017 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <client_http.hpp>
#include <service_record.h>
#include <logger.h>
#include <string>

using HttpClient = SimpleWeb::Client<SimpleWeb::HTTP>;

class ManagementClient {
	public:
		ManagementClient(const std::string& hostname, const short port);
		~ManagementClient();
		bool registerService(const ServiceRecord& service);
	private:
		HttpClient		*m_client;
		std::string		*m_uuid;
		Logger			*m_logger;
};

#endif
