/*
 * FogLAMP core microservice management API.
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch, Massimiliano Pinto
 */
#include <core_management_api.h>
#include <service_registry.h>
#include <rapidjson/document.h>

using namespace std;
using HttpServer = SimpleWeb::Server<SimpleWeb::HTTP>;
using namespace rapidjson;

CoreManagementApi *CoreManagementApi::m_instance = 0;


/**
 * Wrapper for service registration method
 */
void registerMicroServiceWrapper(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request)
{
        CoreManagementApi *api = CoreManagementApi::getInstance();
        api->registerMicroService(response, request);
}

/**
 * Wrapper for service registration method
 */
void unRegisterMicroServiceWrapper(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request)
{
        CoreManagementApi *api = CoreManagementApi::getInstance();
        api->unRegisterMicroService(response, request);
}

/**
 * Wrapper function for the default resource call.
 * This is called whenever an unrecognised entry point call is received.
 */
void defaultWrapper(shared_ptr<HttpServer::Response> response,
		    shared_ptr<HttpServer::Request> request)
{
	CoreManagementApi *api = CoreManagementApi::getInstance();
	api->defaultResource(response, request);
}


/**
 * Handle a bad URL endpoint call
 */
void CoreManagementApi::defaultResource(shared_ptr<HttpServer::Response> response,
					shared_ptr<HttpServer::Request> request)
{
	string payload("{ \"error\" : \"Unsupported URL: " + request->path + "\" }");
	respond(response,
		SimpleWeb::StatusCode::client_error_bad_request,
		payload);
}

/**
 * Construct a microservices management API manager class
 */
CoreManagementApi::CoreManagementApi(const string& name, const unsigned short port) : ManagementApi(name, port)
{
	// Services
	m_server->resource[REGISTER_SERVICE]["POST"] = registerMicroServiceWrapper;
	m_server->resource[UNREGISTER_SERVICE]["DELETE"] = unRegisterMicroServiceWrapper;

	// Default wrapper
	m_server->default_resource["GET"] = defaultWrapper;

	// Set the ihnstance
	m_instance = this;
}

/**
 * Return the singleton instance of the core management interface
 *
 * Note if one has not been explicitly created then this will
 * return 0.
 */
CoreManagementApi *CoreManagementApi::getInstance()
{
	return m_instance;
}

/**
 * Received a service registration request
 */
void CoreManagementApi::registerMicroService(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request)
{
ostringstream convert;
string uuid, payload, responsePayload;

	try {
		ServiceRegistry *registry = ServiceRegistry::getInstance();
		payload = request->content.string();

		Document doc;
		if (doc.Parse(payload.c_str()).HasParseError())
		{
		}
		else
		{
			string name, type, protocol, address;
			unsigned short port, managementPort;
			if (doc.HasMember("name"))
			{
				name = string(doc["name"].GetString());
			}
			if (doc.HasMember("type"))
			{	
				type = string(doc["type"].GetString());
			}
			if (doc.HasMember("address"))
			{
				address = string(doc["address"].GetString());
			}
			if (doc.HasMember("protocol"))
			{
				protocol = string(doc["protocol"].GetString());
			}
			if (doc.HasMember("port"))
			{
				port = doc["port"].GetUint();
			}
			if (doc.HasMember("management_port"))
			{
				managementPort = doc["management_port"].GetUint();
			}
			ServiceRecord *srv = new ServiceRecord(name, type, protocol, address, port, managementPort);
			if (!registry->registerService(srv))
			{
				errorResponse(response, SimpleWeb::StatusCode::client_error_bad_request, "register service", "Failed to register service");
				return;
			}
			uuid = registry->getUUID(srv);
		}

		convert << "{ \"id\" : " << uuid << ",";
		convert << "\"message\" : \"Service registered successfully\"";
		convert << " }";
		responsePayload = convert.str();
		respond(response, responsePayload);
	} catch (exception ex) {
		internalError(response, ex);
	}
}

/**
 * Received a service unregister request
 */
void CoreManagementApi::unRegisterMicroService(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request)
{
ostringstream convert;

	try {
		ServiceRegistry *registry = ServiceRegistry::getInstance();
                string uuid = request->path_match[UUID_COMPONENT];

		if (registry->unRegisterService(uuid))
		{
			convert << "{ \"id\" : " << uuid << ",";
			convert << "\"message\" : \"Service unregistered successfully\"";
			convert << " }";
			string payload = convert.str();
			respond(response, payload);
		}
		else
		{
			errorResponse(response, SimpleWeb::StatusCode::client_error_bad_request, "unregister service", "Failed to unregister service");
		}

	} catch (exception ex) {
		internalError(response, ex);
	}
}
/**
 * Send back an error response
 *
 * @param response	The HTTP Response
 * @param statusCode	The HTTP status code
 * @param entryPoint	The entry point in the API
 * @param msg		The actual error message
 */
void CoreManagementApi::errorResponse(shared_ptr<HttpServer::Response> response,
		SimpleWeb::StatusCode statusCode, const string& entryPoint, const string& msg)
{
ostringstream convert;

	convert << "{ \"message\" : \"" << msg << "\",";
	convert << "\"entryPoint\" : \"" << entryPoint << "\" }";
	respond(response, statusCode, convert.str());
}
/**
 * Handle a exception by sending back an internal error
 *
 * @param response	The HTTP response
 * @param ex		The exception that caused the error
 */
void CoreManagementApi::internalError(shared_ptr<HttpServer::Response> response, const exception& ex)
{
string payload = "{ \"Exception\" : \"";

        payload = payload + string(ex.what());
        payload = payload + "\" }";

        Logger *logger = Logger::getLogger();
        logger->error("CoreManagementApi Internal Error: %s\n", ex.what());
        respond(response, SimpleWeb::StatusCode::server_error_internal_server_error, payload);
}


/**
 * HTTP response method
 */
void CoreManagementApi::respond(shared_ptr<HttpServer::Response> response, const string& payload)
{
        *response << "HTTP/1.1 200 OK\r\nContent-Length: " << payload.length() << "\r\n"
                 <<  "Content-type: application/json\r\n\r\n" << payload;
}

/**
 * HTTP response method
 */
void CoreManagementApi::respond(shared_ptr<HttpServer::Response> response, SimpleWeb::StatusCode statusCode, const string& payload)
{
        *response << "HTTP/1.1 " << status_code(statusCode) << "\r\nContent-Length: " << payload.length() << "\r\n"
                 <<  "Content-type: application/json\r\n\r\n" << payload;
}
