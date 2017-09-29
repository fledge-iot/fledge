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
#include <sstream>

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

/**
 * Construct a microservices management API manager class
 */
ManagementApi::ManagementApi(const string& name, const unsigned short port) : m_name(name)
{
	m_server = new HttpServer();
	m_logger = Logger::getLogger();
	m_server->config.port = port;
	m_startTime = time(0);
	m_statsProvider = 0;
	m_server->resource[PING]["GET"] = pingWrapper;

	m_instance = this;

	m_logger->info("Starting management api on port %d.", port);
}

/**
 * Start HTTP server for management API
 */
static void startService()
{
        ManagementApi::getInstance()->startServer();
}

void ManagementApi::start() {
        m_thread = new thread(startService);
}

void ManagementApi::startServer() {
	m_server->start();
}

/**
 * Return the signleton instance of the management interface
 *
 * Note if one has not been explicitly created then this will
 * return 0.
 */
ManagementApi *ManagementApi::getInstance()
{
	return m_instance;
}

/**
 * Management API destructor
 */
ManagementApi::~ManagementApi()
{
	delete m_server;
}

/**
 * Register a statistics provider
 */
void ManagementApi::registerStats(JSONProvider *statsProvider)
{
	m_statsProvider = statsProvider;
}

/**
 * Received a ping request, construct a reply and return to caller
 */
void ManagementApi::ping(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request)
{
ostringstream convert;
string responsePayload;

	(void)request;	// Unsused argument
	convert << "{ \"uptime\" : " << time(0) - m_startTime << ",";
	convert << "\"name\" : \"" << m_name << "\"";
	if (m_statsProvider)
	{
		string stats;
		m_statsProvider->asJSON(stats);
		convert << ", \"statistics\" : " << stats;
	}
	convert << " }";
	responsePayload = convert.str();
	respond(response, responsePayload);
}

/**
 * HTTP response method
 */
void ManagementApi::respond(shared_ptr<HttpServer::Response> response, const string& payload)
{
        *response << "HTTP/1.1 200 OK\r\nContent-Length: " << payload.length() << "\r\n"
                 <<  "Content-type: application/json\r\n\r\n" << payload;
}
