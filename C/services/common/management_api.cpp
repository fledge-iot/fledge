/*
 * Fledge storage service.
 *
 * Copyright (c) 2017 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <management_api.h>
#include <config_handler.h>
#include <rapidjson/document.h>
#include <logger.h>
#include <time.h>
#include <sstream>

using namespace std;
using namespace rapidjson;
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
 * Wrapper for shutdown method
 */
void shutdownWrapper(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request)
{
        ManagementApi *api = ManagementApi::getInstance();
        api->shutdown(response, request);
}

/**
 * Wrapper for config change method
 */
void configChangeWrapper(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request)
{
        ManagementApi *api = ManagementApi::getInstance();
        api->configChange(response, request);
}

/**
 * Wrapper for config child  create method
 */
void configChildCreateWrapper(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request)
{
        ManagementApi *api = ManagementApi::getInstance();
        api->configChildCreate(response, request);
}

/**
 * Wrapper for config child delete method
 */
void configChildDeleteWrapper(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request)
{
        ManagementApi *api = ManagementApi::getInstance();
        api->configChildDelete(response, request);
}

/**
 * Wrapper for security change method
 */
void securityChangeWrapper(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request)
{
        ManagementApi *api = ManagementApi::getInstance();
        api->securityChange(response, request);
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
	m_server->resource[SERVICE_SHUTDOWN]["POST"] = shutdownWrapper;
	m_server->resource[CONFIG_CHANGE]["POST"] = configChangeWrapper;
	m_server->resource[CONFIG_CHILD_CREATE]["POST"] = configChildCreateWrapper;
	m_server->resource[CONFIG_CHILD_DELETE]["DELETE"] = configChildDeleteWrapper;
	m_server->resource[SECURITY_CHANGE]["PUT"] = securityChangeWrapper;

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

void ManagementApi::stop()
{
	this->stopServer();
}

void ManagementApi::stopServer()
{
	m_server->stop();
	m_thread->join();
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
	delete m_thread;
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
 * Received a shutdown request, construct a reply and return to caller
 */
void ManagementApi::shutdown(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request)
{
ostringstream convert;
string responsePayload;

	(void)request;	// Unsused argument
	m_serviceHandler->shutdown();
	convert << "{ \"message\" : \"Shutdown in progress\" }";
	responsePayload = convert.str();
	respond(response, responsePayload);
}

/**
 * Received a config change request, construct a reply and return to caller
 */
void ManagementApi::configChange(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request)
{
ostringstream convert;
string responsePayload;
string payload;

	try
	{	
		payload = request->content.string();
		ConfigCategoryChange conf(payload);
		ConfigHandler	*handler = ConfigHandler::getInstance(NULL);
		handler->configChange(conf.getName(), conf.itemsToJSON(true));
		convert << "{ \"message\" : \"Config change accepted\" }";
	}
	catch(const std::exception& e)
	{
		convert << "{ \"exception\" : \"" << e.what() << "\" }";
	}
	catch(...)
	{
		convert << "{ \"exception\" : \"generic\" }";
	}
	
	responsePayload = convert.str();
	respond(response, responsePayload);
}

/**
 * Received a children deletion request, construct a reply and return to caller
 */
void ManagementApi::configChildDelete(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request)
{
ostringstream convert;
string responsePayload;
string	category, items, payload, parent_category;

	payload = request->content.string();

	ConfigCategoryChange	conf(payload);
	ConfigHandler	*handler = ConfigHandler::getInstance(NULL);

	parent_category = conf.getmParentName();
	category = conf.getName();
	items = conf.itemsToJSON(true);

	Logger::getLogger()->debug("%s - parent_category:%s: child_category:%s: items:%s: ", __FUNCTION__
							   , parent_category.c_str()
							   , category.c_str()
							   , items.c_str()
							   );

	handler->configChildDelete(parent_category, category);
	convert << "{ \"message\" ; \"Config child category change accepted\" }";
	responsePayload = convert.str();
	respond(response, responsePayload);
}

/**
 * Received a children creation request, construct a reply and return to caller
 */
void ManagementApi::configChildCreate(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request)
{
ostringstream convert;
string responsePayload;
string	category, items, payload, parent_category;

	payload = request->content.string();

	ConfigCategoryChange	conf(payload);
	ConfigHandler	*handler = ConfigHandler::getInstance(NULL);

	parent_category = conf.getmParentName();
	category = conf.getName();
	items = conf.itemsToJSON(true);

	Logger::getLogger()->debug("%s - parent_category:%s: child_category:%s: items:%s: ", __FUNCTION__
							   , parent_category.c_str()
							   , category.c_str()
							   , items.c_str()
							   );

	handler->configChildCreate(parent_category, category, items);
	convert << "{ \"message\" ; \"Config child category change accepted\" }";
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

/**
 * Received a security change request, construct a reply and return to caller
 */
void ManagementApi::securityChange(shared_ptr<HttpServer::Response> response,
				shared_ptr<HttpServer::Request> request)
{
	string payload = request->content.string();

	Logger::getLogger()->debug("Received securityChange: %s", payload.c_str());

	ostringstream convert;
	string responsePayload;

	// Call server securityChange method
	m_serviceHandler->securityChange(payload);

	convert << "{ \"message\" : \"Security change accepted\" }";

	responsePayload = convert.str();
	respond(response, responsePayload);
}
