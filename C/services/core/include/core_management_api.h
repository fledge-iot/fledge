#ifndef _CORE_MANAGEMENT_API_H
#define _CORE_MANAGEMENT_API_H
/*
 * FogLAMP core microservice management API.
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch, Massimiliano Pinto
 */
#include <management_api.h>

#define REGISTER_SERVICE	"/foglamp/service"
#define UNREGISTER_SERVICE	"/foglamp/service/([0-9A-F][0-9A-F\\-]*)"

#define UUID_COMPONENT		1

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
		// Default handler for unsupported URLs
		void			defaultResource(std::shared_ptr<HttpServer::Response> response,
							std::shared_ptr<HttpServer::Request> request);
	private:
		static CoreManagementApi *m_instance;
		void 		errorResponse(
					std::shared_ptr<HttpServer::Response> response,
		               		SimpleWeb::StatusCode statusCode,
					const std::string& entryPoint,
					const std::string& msg);
		void			internalError(std::shared_ptr<HttpServer::Response>, const std::exception&);
		void		respond(
					std::shared_ptr<HttpServer::Response> response,
					SimpleWeb::StatusCode statusCode,
					const std::string& payload);
		void		respond(
					std::shared_ptr<HttpServer::Response> response,
					const std::string& payload);
};
#endif
