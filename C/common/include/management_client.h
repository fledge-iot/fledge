#ifndef _MANAGEMENT_CLIENT_H
#define _MANAGEMENT_CLIENT_H
/*
 * Fledge storage service.
 *
 * Copyright (c) 2017-2018 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch, Massimiliano Pinto
 */
#include <client_http.hpp>
#include <config_category.h>
#include <service_record.h>
#include <logger.h>
#include <string>
#include <map>
#include <rapidjson/document.h>
#include <asset_tracking.h>
#include <json_utils.h>
#include <thread>

using HttpClient = SimpleWeb::Client<SimpleWeb::HTTP>;
using namespace rapidjson;

class AssetTrackingTuple;

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
                std::string             setCategoryItemValue(const std::string& categoryName,
                                                             const std::string& itemName,
                                                             const std::string& itemValue);
		std::string		addChildCategories(const std::string& parentCategory,
							   const std::vector<std::string>& children);
		std::vector<AssetTrackingTuple*>&	getAssetTrackingTuples(const std::string serviceName);
		bool addAssetTrackingTuple(const std::string& service, 
					   const std::string& plugin, 
					   const std::string& asset, 
					   const std::string& event);
		ConfigCategories	getChildCategories(const std::string& categoryName);
		HttpClient		*getHttpClient();
		bool			addAuditEntry(const std::string& serviceName,
						      const std::string& severity,
						      const std::string& details);
		std::string&		getBearerToken() { return m_bearer_token; };

private:
    std::ostringstream 			m_urlbase;
		std::map<std::thread::id, HttpClient *> m_client_map;
		HttpClient				*m_client;
		std::string				*m_uuid;
		Logger					*m_logger;
		std::map<std::string, std::string>	m_categories;
		// Bearer token returned by service registration
		// if the service startup token has been passed in registration payload
		std::string				m_bearer_token;
  
	public:
		// member template must be here and not in .cpp file
		template<class T> bool	addCategory(const T& t, bool keepOriginalItems = false)
		{
			try {
				std::string url = "/fledge/service/category";

                                // Build the JSON payload
                                std::ostringstream payload;
                                payload << "{ \"key\" : \"" << JSONescape(t.getName());
                                payload << "\", \"description\" : \"" << JSONescape(t.getDescription());
                                if (! t.getDisplayName().empty() ) {
                                	payload << "\", \"display_name\" : \"" << JSONescape(t.getDisplayName());
                                }
                                payload << "\", \"value\" : " << t.itemsToJSON();


				/**
				 * Note:
				 * At the time being the keep_original_items is added into payload
				 * and configuration manager in the Fledge handles it.
				 *
				 * In the near future keep_original_items will be passed
				 * as URL modifier, i.e: 'URL?keep_original_items=true'
				 */
				if (keepOriginalItems)
				{
					url += "?keep_original_items=true";
				}

				// Terminate JSON string
				payload << " }";

				auto res = this->getHttpClient()->request("POST", url.c_str(), payload.str());

				Document doc;
				std::string response = res->content.string();

				doc.Parse(response.c_str());
				if (doc.HasParseError())
				{
					m_logger->error("Failed to parse result of adding a category: %s\n",
							response.c_str());
					return false;
				}
				else if (doc.HasMember("message"))
				{
					m_logger->error("Failed to add configuration category: %s.",
							doc["message"].GetString());
					return false;
				}
				else
				{
					return true;
				}
			} catch (const SimpleWeb::system_error &e) {
				m_logger->error("Add config category failed %s.", e.what());
			}
			return false;
		};
};

#endif
