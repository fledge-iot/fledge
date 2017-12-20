/*
 * FogLAMP storage service.
 *
 * Copyright (c) 2017 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include "client_http.hpp"
#include "server_http.hpp"
#include "storage_api.h"
#include "storage_stats.h"
#include "management_api.h"
#include "logger.h"


// Added for the default_resource example
#include <algorithm>
#include <fstream>
#include <vector>
#ifdef HAVE_OPENSSL
#include "crypto.hpp"
#endif

/**
 * Definition of the Storage Service REST API
 */

StorageApi *StorageApi::m_instance = 0;

using namespace std;
using HttpServer = SimpleWeb::Server<SimpleWeb::HTTP>;
using HttpClient = SimpleWeb::Client<SimpleWeb::HTTP>;

/**
 * The following are a set of wrapper C functions that are registered with the HTTP Server
 * for each of the API entry poitns. These must be outside if a class as the library has no
 * mechanism to have a class isntance and hence can not provide a "this" pointer for the callback.
 *
 * These functions do the minumum work needed to find the singleton instance of the StorageAPI
 * class and call the appriopriate method of that class to the the actual work.
 */

/**
 * Wrapper function for the common insert API call.
 */
void commonInsertWrapper(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request)
{
	StorageApi *api = StorageApi::getInstance();
	api->commonInsert(response, request);
}

/**
 * Wrapper function for the common update API call.
 */
void commonUpdateWrapper(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request)
{
	StorageApi *api = StorageApi::getInstance();
	api->commonUpdate(response, request);
}

/**
 * Wrapper function for the common delete API call.
 */
void commonDeleteWrapper(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request)
{
	StorageApi *api = StorageApi::getInstance();
	api->commonDelete(response, request);
}

/**
 * Wrapper function for the common simle query API call.
 */
void commonSimpleQueryWrapper(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request)
{
	StorageApi *api = StorageApi::getInstance();
	api->commonSimpleQuery(response, request);
}

/**
 * Wrapper function for the common query API call.
 */
void commonQueryWrapper(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request)
{
	StorageApi *api = StorageApi::getInstance();
	api->commonQuery(response, request);
}

/**
 * Wrapper function for the default resource API call. This is called whenever
 * an unrecognised API call is received.
 */
void defaultWrapper(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request)
{
	StorageApi *api = StorageApi::getInstance();
	api->defaultResource(response, request);
}

/**
 * Called when an error occurs
 */
void on_error(__attribute__((unused)) shared_ptr<HttpServer::Request> request, __attribute__((unused)) const SimpleWeb::error_code &ec) {
}

/**
 * Wrapper function for the reading appendAPI call.
 */
void readingAppendWrapper(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request)
{
	StorageApi *api = StorageApi::getInstance();
	api->readingAppend(response, request);
}

/**
 * Wrapper function for the reading fetch API call.
 */
void readingFetchWrapper(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request)
{
	StorageApi *api = StorageApi::getInstance();
	api->readingFetch(response, request);
}

/**
 * Wrapper function for the reading query API call.
 */
void readingQueryWrapper(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request)
{
	StorageApi *api = StorageApi::getInstance();
	api->readingQuery(response, request);
}

/**
 * Wrapper function for the reading purge API call.
 */
void readingPurgeWrapper(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request)
{
	StorageApi *api = StorageApi::getInstance();
	api->readingPurge(response, request);
}

/**
 * Construct the singleton Storage API 
 */
StorageApi::StorageApi(const unsigned short port, const int threads) {

	m_port = port;
	m_threads = threads;
	m_server = new HttpServer();
	m_server->config.port = port;
	StorageApi::m_instance = this;
}

/**
 * Return the singleton instance of the StorageAPI class
 */
StorageApi *StorageApi::getInstance()
{
	if (m_instance == NULL)
	{
		m_instance = new StorageApi(0, 1);
	}
	return m_instance;
}

/**
 * Return the current listener port
 */
unsigned short StorageApi::getListenerPort()
{
	return m_server->getLocalPort();
}

/**
 * Initialise the API entry points for the common data resource and
 * the readings resource.
 */
void StorageApi::initResources()
{
	m_server->resource[COMMON_ACCESS]["POST"] = commonInsertWrapper;
	m_server->resource[COMMON_ACCESS]["GET"] = commonSimpleQueryWrapper;
	m_server->resource[COMMON_QUERY]["PUT"] = commonQueryWrapper;
	m_server->resource[COMMON_ACCESS]["PUT"] = commonUpdateWrapper;
	m_server->resource[COMMON_ACCESS]["DELETE"] = commonDeleteWrapper;
	m_server->default_resource["POST"] = defaultWrapper;
	m_server->default_resource["PUT"] = defaultWrapper;
	m_server->default_resource["GET"] = defaultWrapper;
	m_server->default_resource["DELETE"] = defaultWrapper;
	m_server->resource[READING_ACCESS]["POST"] = readingAppendWrapper;
	m_server->resource[READING_ACCESS]["GET"] = readingFetchWrapper;
	m_server->resource[READING_QUERY]["PUT"] = readingQueryWrapper;
	m_server->resource[READING_PURGE]["PUT"] = readingPurgeWrapper;

	m_server->on_error = on_error;

	ManagementApi *management = ManagementApi::getInstance();
	management->registerStats(&stats);
}

void startService()
{
	StorageApi::getInstance()->startServer();
}

/**
 * Start the HTTP server
 */
void StorageApi::start() {
	m_thread = new thread(startService);
}

void StorageApi::startServer() {
	m_server->start();
}

void StorageApi::stopServer() {
	m_server->stop();
}
/**
 * Wait for the HTTP server to shutdown
 */
void StorageApi::wait() {
	m_thread->join();
}

/**
 * Connect with the storage plugin
 */
void StorageApi::setPlugin(StoragePlugin *plugin)
{
	this->plugin = plugin;
}

/**
 * Construct an HTTP response with the 200 OK return code using the payload
 * provided.
 *
 * @param response The response stream to send the response on
 * @param payload  The payload to send
 */
void StorageApi::respond(shared_ptr<HttpServer::Response> response, const string& payload)
{
	*response << "HTTP/1.1 200 OK\r\nContent-Length: " << payload.length() << "\r\n"
		 <<  "Content-type: application/json\r\n\r\n" << payload;
}


/**
 * Construct an HTTP response with the specified return code using the payload
 * provided.
 *
 * @param response 	The response stream to send the response on
 * @param code		The HTTP esponse code to send
 * @param payload  	The payload to send
 */
void StorageApi::respond(shared_ptr<HttpServer::Response> response, SimpleWeb::StatusCode code, const string& payload)
{
	*response << "HTTP/1.1 " << status_code(code) << "\r\nContent-Length: " << payload.length() << "\r\n"
		 <<  "Content-type: application/json\r\n\r\n" << payload;
}

/**
 * Perform an insert into a table of the data provided in the payload.
 *
 * @param response	The response stream to send the response on
 * @param request	The HTTP request
 */
void StorageApi::commonInsert(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request)
{
string  tableName;
string	payload;
string  responsePayload;

	stats.commonInsert++;
	try {
		tableName = request->path_match[TABLE_NAME_COMPONENT];
		payload = request->content.string();

		int rval = plugin->commonInsert(tableName, payload);
		if (rval != -1)
		{
			responsePayload = "{ \"response\" : \"inserted\", \"rows_affected\" : ";
			responsePayload += to_string(rval);
			responsePayload += " }";
			respond(response, responsePayload);
		}
		else
		{
			mapError(responsePayload, plugin->lastError());
			respond(response, SimpleWeb::StatusCode::client_error_bad_request, responsePayload);
		}
		respond(response, responsePayload);
	} catch (exception ex) {
		internalError(response, ex);
	}
}

/**
 * Perform an update on a table of the data provided in the payload.
 *
 * @param response	The response stream to send the response on
 * @param request	The HTTP request
 */
void StorageApi::commonUpdate(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request)
{
string  tableName;
string	payload;
string	responsePayload;

	stats.commonUpdate++;
	try {
		tableName = request->path_match[TABLE_NAME_COMPONENT];
		payload = request->content.string();

		int rval = plugin->commonUpdate(tableName, payload);
		if (rval != -1)
		{
			responsePayload = "{ \"response\" : \"updated\", \"rows_affected\"  : ";
			responsePayload += to_string(rval);
			responsePayload += " }";
			respond(response, responsePayload);
		}
		else
		{
			mapError(responsePayload, plugin->lastError());
			respond(response, SimpleWeb::StatusCode::client_error_bad_request, responsePayload);
		}

	} catch (exception ex) {
		internalError(response, ex);
		}
}

/**
 * Perform a simple query on the table using the query parameters as conditions
 * TODO make this work for multiple column queries
 *
 * @param response	The response stream to send the response on
 * @param request	The HTTP request
 */
void StorageApi::commonSimpleQuery(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request)
{
string  tableName;
SimpleWeb::CaseInsensitiveMultimap	query;
string payload;

	stats.commonSimpleQuery++;
	try {
		tableName = request->path_match[TABLE_NAME_COMPONENT];
		query = request->parse_query_string();

		if (query.size() > 0)
		{
			payload = "{ \"where\" : { ";
			for(auto &param : query)
			{
				payload = payload + "\"column\" :  \"";
				payload = payload + param.first;
				payload = payload + "\", \"condition\" : \"=\", \"value\" : \"";
				payload = payload + param.second;
				payload = payload + "\"";
			}
			payload = payload + "} }";
		}

		char *pluginResult = plugin->commonRetrieve(tableName, payload);
		if (pluginResult)
		{
			string res = pluginResult;

			respond(response, res);
			free(pluginResult);
		}
		else
		{
			string responsePayload;
			mapError(responsePayload, plugin->lastError());
			respond(response, SimpleWeb::StatusCode::client_error_bad_request, responsePayload);
		}
	} catch (exception ex) {
		internalError(response, ex);
	}
}

/**
 * Perform query on a table using the JSON encoded query in the payload
 *
 * @param response	The response stream to send the response on
 * @param request	The HTTP request
 */
void StorageApi::commonQuery(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request)
{
string  tableName;
string	payload;

	stats.commonQuery++;
	try {
		tableName = request->path_match[TABLE_NAME_COMPONENT];
		payload = request->content.string();

		char *pluginResult = plugin->commonRetrieve(tableName, payload);
		if (pluginResult)
		{
			string res = pluginResult;

			respond(response, res);
			free(pluginResult);
		}
		else
		{
			string responsePayload;
			mapError(responsePayload, plugin->lastError());
			respond(response, SimpleWeb::StatusCode::client_error_bad_request, responsePayload);
		}

	} catch (exception ex) {
		internalError(response, ex);
	}
}

/**
 * Perform a delete on a table using the condition encoded in the JSON payload
 *
 * @param response	The response stream to send the response on
 * @param request	The HTTP request
 */
void StorageApi::commonDelete(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request)
{
string  tableName;
string	payload;
string  responsePayload;

	stats.commonDelete++;
	try {
		tableName = request->path_match[TABLE_NAME_COMPONENT];
		payload = request->content.string();

		int rval = plugin->commonDelete(tableName, payload);
		if (rval != -1)
		{
			responsePayload = "{ \"response\" : \"deleted\", \"rows_affected\"  : ";
			responsePayload += to_string(rval);
			responsePayload += " }";
			respond(response, responsePayload);
		}
		else
		{
			mapError(responsePayload, plugin->lastError());
			respond(response, SimpleWeb::StatusCode::client_error_bad_request, responsePayload);
		}

		respond(response, responsePayload);
	} catch (exception ex) {
		internalError(response, ex);
	}
}

/**
 * Perform an append operation on the readings.
 *
 * @param response	The response stream to send the response on
 * @param request	The HTTP request
 */
void StorageApi::readingAppend(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request)
{
string payload;
string  responsePayload;

	stats.readingAppend++;
	try {
		payload = request->content.string();
		int rval = plugin->readingsAppend(payload);
		if (rval != -1)
		{
			responsePayload = "{ \"response\" : \"appended\", \"readings_added\" : ";
			responsePayload += to_string(rval);
			responsePayload += " }";
			respond(response, responsePayload);
		}
		else
		{
			mapError(responsePayload, plugin->lastError());
			respond(response, SimpleWeb::StatusCode::client_error_bad_request, responsePayload);
		}

		respond(response, responsePayload);
	} catch (exception ex) {
		internalError(response, ex);
	}
}

/**
 * Fetch a block of readings.
 *
 * @param response	The response stream to send the response on
 * @param request	The HTTP request
 */
void StorageApi::readingFetch(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request)
{
SimpleWeb::CaseInsensitiveMultimap query;
unsigned long			   id = 0;
unsigned long			   count = 0;
string				   responsePayload;

	stats.readingFetch++;
	try {
		query = request->parse_query_string();

		auto search = query.find("id");
		if (search == query.end())
		{
			string payload = "{ \"error\" : \"Missing query parameter id\" }";
			respond(response, SimpleWeb::StatusCode::client_error_bad_request, payload);
			return;
		}
		else
		{
			id = (unsigned)atol(search->second.c_str());
		}
		search = query.find("count");
		if (search == query.end())
		{
			string payload = "{ \"error\" : \"Missing query parameter count\" }";
			respond(response, SimpleWeb::StatusCode::client_error_bad_request, payload);
			return;
		}
		else
		{
			count = (unsigned)atol(search->second.c_str());
		}

		responsePayload = plugin->readingsFetch(id, count);

		respond(response, responsePayload);
	} catch (exception ex) {
		internalError(response, ex);
	}
}

/**
 * Perform a query on a set of readings
 *
 * @param response	The response stream to send the response on
 * @param request	The HTTP request
 */
void StorageApi::readingQuery(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request)
{
string	payload;

	stats.readingQuery++;
	try {
		payload = request->content.string();

		char *resultSet = plugin->readingsRetrieve(payload);
		string res = resultSet;

		respond(response, res);
		free(resultSet);
	} catch (exception ex) {
		internalError(response, ex);
	}
}


/**
 * Purge the readings
 *
 * @param response	The response stream to send the response on
 * @param request	The HTTP request
 */
void StorageApi::readingPurge(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request)
{
SimpleWeb::CaseInsensitiveMultimap query;
unsigned long age = 0;
unsigned long size = 0;
unsigned long lastSent = 0;
unsigned int  flagsMask = 0;
string        flags;

	stats.readingPurge++;
	try {
		query = request->parse_query_string();

		auto search = query.find("age");
		if (search != query.end())
		{
			age = (unsigned)atol(search->second.c_str());
		}
		search = query.find("size");
		if (search != query.end())
		{
			size = (unsigned)atol(search->second.c_str());
		}
		search = query.find("sent");
		if (search == query.end())
		{
			string payload = "{ \"error\" : \"Missing query parameter sent\" }";
			respond(response, SimpleWeb::StatusCode::client_error_bad_request, payload);
			return;
		}
		else
		{
			lastSent = (unsigned)atol(search->second.c_str());
		}

		search = query.find("flags");
		if (search != query.end())
		{
			flags = search->second;
			// TODO Turn flags into a bitmap
			if (flags.compare(PURGE_FLAG_RETAIN) == 0)
			{
				flagsMask |= STORAGE_PURGE_RETAIN;
			}
			else if (flags.compare(PURGE_FLAG_PURGE) == 0)
			{
				flagsMask &= (~STORAGE_PURGE_RETAIN);
			}
		}

		char *purged = NULL;
		if (age)
		{
			purged = plugin->readingsPurge(age, flagsMask, lastSent);
		}
		else if (size)
		{
			purged = plugin->readingsPurge(size, flagsMask|STORAGE_PURGE_SIZE, lastSent);
		}
		else
		{
			string payload = "{ \"error\" : \"Must either specify age or size parameter\" }";
			respond(response, SimpleWeb::StatusCode::client_error_bad_request, payload);
			return;
		}
		string responsePayload = purged;
		respond(response, responsePayload);
	} catch (exception ex) {
		internalError(response, ex);
	}
}

/**
 * Handle a bad URL endpoint call
 */
void StorageApi::defaultResource(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request)
{
string	payload;

	payload = "{ \"error\" : \"Unsupported URL: " + request->path + "\" }";
	respond(response, SimpleWeb::StatusCode::client_error_bad_request, payload);
}

/**
 * Handle a exception by sendign back an internal error
 */
void StorageApi::internalError(shared_ptr<HttpServer::Response> response, const exception& ex)
{
string payload = "{ \"Exception\" : \"";

	payload = payload + string(ex.what());
	payload = payload + "\"";

	Logger *logger = Logger::getLogger();
	logger->error("StorgeApi Internal Error: %s\n", ex.what());
	respond(response, SimpleWeb::StatusCode::server_error_internal_server_error, payload);
}

void StorageApi::mapError(string& payload, PLUGIN_ERROR *lastError)
{
char *ptr, *ptr1, *buf = new char[strlen(lastError->message) * 2 + 1];

	ptr = buf;
	ptr1 = lastError->message;
	while (*ptr1)
	{
		if (*ptr1 == '"')
			*ptr++ = '\\';
		*ptr++ = *ptr1++;
	}
	*ptr = 0;
	payload = "{ \"entryPoint\" : \"";
	payload = payload + lastError->entryPoint;
	payload = payload + "\", \"message\" : \"";
	payload = payload + buf;
	payload = payload + "\", \"retryable\" : ";
	payload = payload + (lastError->retryable ? "true" : "false");
	payload = payload + "}";
	delete[] buf;
}
