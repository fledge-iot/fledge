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
#include <server_http.hpp>
#include <config_category.h>
#include <service_record.h>
#include <logger.h>
#include <string>
#include <map>
#include <vector>
#include <rapidjson/document.h>
#include <asset_tracking.h>
#include <json_utils.h>
#include <thread>
#include <bearer_token.h>
#include <acl.h>

using HttpClient = SimpleWeb::Client<SimpleWeb::HTTP>;
using HttpServer = SimpleWeb::Server<SimpleWeb::HTTP>;
using namespace rapidjson;

class AssetTrackingTuple;
class AssetTrackingTable;
class StorageAssetTrackingTuple;

/**
 * The management client class used by services and tasks to communicate
 * with the management API of the Fledge core microservice.
 *
 * The class encapsulates the management REST API and provides methods for accessing each
 * of those APIs.
 */
class ManagementClient {
	public:
		ManagementClient(const std::string& hostname, const unsigned short port);
		~ManagementClient();
		bool 			registerService(const ServiceRecord& service);
		bool 			unregisterService();
		bool 			restartService();
		bool 			getService(ServiceRecord& service);
		bool			getServices(std::vector<ServiceRecord *>& services);
		bool			getServices(std::vector<ServiceRecord *>& services, const std::string& type);
		bool 			registerCategory(const std::string& categoryName);
		bool 			registerCategoryChild(const std::string& categoryName);
		bool 			unregisterCategory(const std::string& categoryName);
		ConfigCategories	getCategories();
		ConfigCategory		getCategory(const std::string& categoryName);
                std::string             setCategoryItemValue(const std::string& categoryName,
                                                             const std::string& itemName,
                                                             const std::string& itemValue);
		std::string		addChildCategories(const std::string& parentCategory,
							   const std::vector<std::string>& children);
		std::vector<AssetTrackingTuple*>&
					getAssetTrackingTuples(const std::string serviceName = "");
		std::vector<StorageAssetTrackingTuple*>&
 					getStorageAssetTrackingTuples(const std::string serviceName);

		StorageAssetTrackingTuple* getStorageAssetTrackingTuple(const std::string& serviceName,
                                                         	const std::string& assetName,
								const std::string& event, const std::string & dp, const unsigned int& c);

		bool addAssetTrackingTuple(const std::string& service, 
					   const std::string& plugin, 
					   const std::string& asset, 
					   const std::string& event);

		bool addStorageAssetTrackingTuple(const std::string& service,
                                           const std::string& plugin,
                                           const std::string& asset,
                                           const std::string& event,
					   const bool& deprecated = false,
					   const std::string& datapoints = "",
					   const int& count = 0);
		ConfigCategories	getChildCategories(const std::string& categoryName);
		HttpClient		*getHttpClient();
		bool			addAuditEntry(const std::string& serviceName,
						      const std::string& severity,
						      const std::string& details);
		std::string&		getRegistrationBearerToken()
		{
					std::lock_guard<std::mutex> guard(m_bearer_token_mtx);
					return m_bearer_token;
		};
		void			setNewBearerToken(const std::string& bearerToken)
					{
						std::lock_guard<std::mutex> guard(m_bearer_token_mtx);
						m_bearer_token = bearerToken;
					};
		bool			verifyBearerToken(BearerToken& token);
		bool			verifyAccessBearerToken(BearerToken& bToken);
		bool			verifyAccessBearerToken(std::shared_ptr<HttpServer::Request> request);
		bool			refreshBearerToken(const std::string& currentToken,
							std::string& newToken);
		std::string&		getBearerToken() { return m_bearer_token; };
		bool			addProxy(const std::string& serviceName,
						const std::string& operation,
						const std::string& publicEnpoint,
						const std::string& privateEndpoint);
		bool			addProxy(const std::string& serviceName,
						const std::map<std::string,
						std::vector<std::pair<std::string, std::string> > >& endpoints);
		bool			deleteProxy(const std::string& serviceName);
		const std::string 	getUrlbase() { return m_urlbase.str(); }
	        ACL			getACL(const std::string& aclName);
		AssetTrackingTuple*	getAssetTrackingTuple(const std::string& serviceName,
								const std::string& assetName,
								const std::string& event);
		int 			validateDatapoints(std::string dp1, std::string dp2);
		AssetTrackingTable	*getDeprecatedAssetTrackingTuples();
		std::string		getAlertByKey(const std::string& key);
		bool			raiseAlert(const std::string& key, const std::string& message, const std::string& urgency="normal");

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
		// Map of received and verified access bearer tokens from other microservices
		std::map<std::string, BearerToken> 	m_received_tokens;
		// m_received_tokens lock
		std::mutex 				m_mtx_rTokens;
		// m_client_map lock
		std::mutex				m_mtx_client_map;
		// Get and set bearer token mutex
		std::mutex				m_bearer_token_mtx;
  
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
