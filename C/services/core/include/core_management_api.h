#ifndef _CORE_MANAGEMENT_API_H
#define _CORE_MANAGEMENT_API_H
/*
 * Fledge core microservice management API.
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch, Massimiliano Pinto
 */
#include <management_api.h>
#include <configuration_manager.h>


#define REGISTER_SERVICE		"/fledge/service"
#define UNREGISTER_SERVICE		"/fledge/service/([0-9A-F][0-9A-F\\-]*)"
#define GET_ALL_CATEGORIES		"/fledge/service/category"
#define CREATE_CATEGORY			GET_ALL_CATEGORIES
#define GET_CATEGORY			"/fledge/service/category/([A-Za-z][a-zA-Z_0-9]*)"
#define GET_CATEGORY_ITEM		"/fledge/service/category/([A-Za-z][a-zA-Z_0-9]*)/([A-Za-z][a-zA-Z_0-9]*)"
#define DELETE_CATEGORY_ITEM_VALUE	"/fledge/service/category/([A-Za-z][a-zA-Z_0-9]*)/([A-Za-z][a-zA-Z_0-9]*)/(value)"
#define SET_CATEGORY_ITEM_VALUE		GET_CATEGORY_ITEM
#define DELETE_CATEGORY			GET_CATEGORY
#define DELETE_CHILD_CATEGORY		"/fledge/service/category/([A-Za-z][a-zA-Z_0-9]*)/(children)/([A-Za-z][a-zA-Z_0-9]*)"
#define ADD_CHILD_CATEGORIES		"/fledge/service/category/([A-Za-z][a-zA-Z_0-9]*)/(children)"
#define REGISTER_CATEGORY_INTEREST	"/fledge/interest"	// TODO implment this, right now it's a fake.
#define GET_SERVICE			REGISTER_SERVICE

#define UUID_COMPONENT			1
#define CATEGORY_NAME_COMPONENT		1
#define CATEGORY_ITEM_COMPONENT		2
#define ITEM_VALUE_NAME			3
#define CHILD_CATEGORY_COMPONENT	3

using HttpServer = SimpleWeb::Server<SimpleWeb::HTTP>;

/**
 * Management API server for a C++ microservice
 */
class CoreManagementApi : public ManagementApi {
	public:
		CoreManagementApi(const std::string& name, const unsigned short port);
		~CoreManagementApi() {};
		static CoreManagementApi *getInstance();
		void			registerMicroService(std::shared_ptr<HttpServer::Response> response,
							     std::shared_ptr<HttpServer::Request> request);
		void			unRegisterMicroService(std::shared_ptr<HttpServer::Response> response,
							       std::shared_ptr<HttpServer::Request> request);
		// GET /fledge/service/category
		void			getAllCategories(std::shared_ptr<HttpServer::Response> response,
							 std::shared_ptr<HttpServer::Request> request);
		// GET /fledge/service/category/{categoryName}
		void			getCategory(std::shared_ptr<HttpServer::Response> response,
						    std::shared_ptr<HttpServer::Request> request);
		// GET /fledge/service/category/{categoryName}/{configItem}
		// GET /fledge/service/category/{categoryName}/children
		void			getCategoryItem(std::shared_ptr<HttpServer::Response> response,
							std::shared_ptr<HttpServer::Request> request);
		// DELETE /fledge/service/category/{categoryName}/{configItem}/value
		void			deleteCategoryItemValue(std::shared_ptr<HttpServer::Response> response,
								std::shared_ptr<HttpServer::Request> request);
		//  PUT /fledge/service/category/{categoryName}/{configItemn}
		void			setCategoryItemValue(std::shared_ptr<HttpServer::Response> response,
							     std::shared_ptr<HttpServer::Request> request);
                // Called by DELETE /fledge/service/category/{categoryName}
		void			deleteCategory(std::shared_ptr<HttpServer::Response> response,
						       std::shared_ptr<HttpServer::Request> request);
		// Called by DELETE /fledge/service/category/{CategoryName}/children/{ChildCategory}
		void			deleteChildCategory(std::shared_ptr<HttpServer::Response> response,
							    std::shared_ptr<HttpServer::Request> request);
		// Called by POST /fledge/service/category
		void			createCategory(std::shared_ptr<HttpServer::Response> response,
						       std::shared_ptr<HttpServer::Request> request);
		// Called by POST /fledge/service/category/{categoryName}/children
		void			addChildCategory(std::shared_ptr<HttpServer::Response> response,
							 std::shared_ptr<HttpServer::Request> request);
		// Default handler for unsupported URLs
		void			defaultResource(std::shared_ptr<HttpServer::Response> response,
							std::shared_ptr<HttpServer::Request> request);

	private:
		void			errorResponse(std::shared_ptr<HttpServer::Response> response,
						      SimpleWeb::StatusCode statusCode,
						      const std::string& entryPoint,
						      const std::string& msg);
		void			internalError(std::shared_ptr<HttpServer::Response>,
						      const std::exception&);
		void			respond(std::shared_ptr<HttpServer::Response> response,
						SimpleWeb::StatusCode statusCode,
						const std::string& payload);
		void			respond(std::shared_ptr<HttpServer::Response> response,
						const std::string& payload);
		bool			getConfigurationManager(const std::string& address,
								const unsigned short port);
		void			setConfigurationEntryPoints();

	private:
		static CoreManagementApi*	m_instance;
		ConfigurationManager*		m_config;
};
#endif
