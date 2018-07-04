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
#include <json_provider.h>
#include <service_handler.h>
#include <server_http.hpp>
#include <logger.h>
#include <string>
#include <time.h>
#include <thread>

#define PING			"/foglamp/service/ping"
#define SERVICE_SHUTDOWN	"/foglamp/service/shutdown"
#define CONFIG_CHANGE		"/foglamp/change"

using HttpServer = SimpleWeb::Server<SimpleWeb::HTTP>;

/**
 * Management API server for a C++ microservice
 */
class ManagementApi {
	public:
		ManagementApi(const std::string& name, const unsigned short port);
		~ManagementApi();
		static ManagementApi *getInstance();
		void start();
		void startServer();
		void registerStats(JSONProvider *statsProvider);
		void registerService(ServiceHandler *serviceHandler) {
			m_serviceHandler = serviceHandler;
		}
		unsigned short getListenerPort() {
			return m_server->getLocalPort();
		}
		void ping(std::shared_ptr<HttpServer::Response> response, std::shared_ptr<HttpServer::Request> request);
		void shutdown(std::shared_ptr<HttpServer::Response> response, std::shared_ptr<HttpServer::Request> request);
		void configChange(std::shared_ptr<HttpServer::Response> response, std::shared_ptr<HttpServer::Request> request);

	protected:
		static ManagementApi *m_instance;
		std::string	m_name;
		Logger		*m_logger;
		time_t		m_startTime;
		HttpServer	*m_server;
		JSONProvider	*m_statsProvider;
		ServiceHandler	*m_serviceHandler;
		std::thread	*m_thread;
	private:
		void            respond(std::shared_ptr<HttpServer::Response>, const std::string&);
};
#endif
