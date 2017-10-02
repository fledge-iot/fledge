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
#include <map>

using HttpClient = SimpleWeb::Client<SimpleWeb::HTTP>;

class ManagementClient {
	public:
		ManagementClient(const std::string& hostname, const short port);
		~ManagementClient();
		bool registerService(const ServiceRecord& service);
		bool unregisterService();
		bool registerCategory(const std::string& category);
		bool unregisterCategory(const std::string& category);
	private:
		HttpClient		*m_client;
		std::string		*m_uuid;
		Logger			*m_logger;
		std::map<std::string, std::string>
					m_categories;
};

#endif
