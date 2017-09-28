#ifndef _MANAGEMENT_API_H
#define _MANAGEMENT_API_H
/*
 * FogLAMP storage service.
 *
 * Copyright (c) 2017 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */

#include <server_http.hpp>
#include <logger.h>
#include <string>
#include <time.h>

#define PING	"/management/ping"

using HttpServer = SimpleWeb::Server<SimpleWeb::HTTP>;

/**
 * Management API server for a C++ microservice
 */
class ManagementApi {
	public:
		ManagementApi(const unsigned short port);
		~ManagementApi();
		static ManagementApi *getInstance();
		void ping(std::shared_ptr<HttpServer::Response> response, std::shared_ptr<HttpServer::Request> request);

	private:
		static ManagementApi *m_instance;
		Logger		*m_logger;
		time_t		m_startTime;
		HttpServer	*m_server;
		void            respond(std::shared_ptr<HttpServer::Response>, const std::string&);
};
#endif
