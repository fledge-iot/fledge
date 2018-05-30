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
#include <config_category.h>
#include <service_record.h>
#include <logger.h>
#include <string>
#include <map>

using HttpClient = SimpleWeb::Client<SimpleWeb::HTTP>;

class ManagementClient {
	public:
		ManagementClient(const std::string& hostname, const unsigned short port);
		~ManagementClient();
		bool 			registerService(const ServiceRecord& service);
		bool 			unregisterService();
		bool 			getService(ServiceRecord& service);
		bool 			registerCategory(const std::string& categoryName);
		bool 			unregisterCategory(const std::string& categoryName);
		ConfigCategories	getCategories();
		ConfigCategory		getCategory(const std::string& categoryName);
		bool			addCategory(const ConfigCategory& category);
	private:
		HttpClient		*m_client;
		std::string		*m_uuid;
		Logger			*m_logger;
		std::map<std::string, std::string>
					m_categories;
};

#endif
