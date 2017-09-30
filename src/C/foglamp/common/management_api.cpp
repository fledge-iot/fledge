/*
 * FogLAMP storage service.
 *
 * Copyright (c) 2017 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <management_api.h>
#include <logger.h>
#include <time.h>

using namespace std;
using HttpServer = SimpleWeb::Server<SimpleWeb::HTTP>;

ManagementApi *ManagementApi::m_instance = 0;

/**
 * Wrapper for ping method
 */
void pingWrapper(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request)
{
        ManagementApi *api = ManagementApi::getInstance();
        api->ping(response, request);
}

ManagementApi::ManagementApi(const unsigned short port)
{
	m_server = new HttpServer();
	m_logger = Logger::getLogger();
	m_server->config.port = port;
	m_startTime = time(0);
	m_server->resource[PING]["GET"] = pingWrapper;

	m_instance = this;

	m_logger->info("Starting management api on port %d.", port);
	m_server->start();
}

ManagementApi *ManagementApi::getInstance()
{
	return m_instance;
}

ManagementApi::~ManagementApi()
{
	delete m_server;
}

void ManagementApi::ping(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request)
{
string responsePayload;

	(void)request;	// Unsused argument
	responsePayload = "{ \"uptime\" : 0 }";
	respond(response, responsePayload);
}

void ManagementApi::respond(shared_ptr<HttpServer::Response> response, const string& payload)
{
        *response << "HTTP/1.1 200 OK\r\nContent-Length: " << payload.length() << "\r\n"
                 <<  "Content-type: application/json\r\n\r\n" << payload;
}
