/*
 * Fledge storage service.
 *
 * Copyright (c) 2017-2018 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch, Massimiliano Pinto
 */
#include "client_http.hpp"
#include "server_http.hpp"
#include "storage_api.h"
#include "storage_stats.h"
#include "management_api.h"
#include "logger.h"
#include "plugin_exception.h"
#include <rapidjson/document.h>
#include <atomic>

// Added for the default_resource example
#include <algorithm>
#include <fstream>
#include <vector>
#ifdef HAVE_OPENSSL
#include "crypto.hpp"
#endif

#include <string_utils.h>

#define WORKER_THREAD_POOL	1
// Enable worker threads for readings append and fetch
#define WORKER_THREADS		1

// Threshold for logging number of threads in use for some "readings" wrappers
#define MAX_WORKER_THREADS	5

/**
 * Definition of the Storage Service REST API
 */

StorageApi *StorageApi::m_instance = 0;

using namespace std;
using namespace rapidjson;
using HttpServer = SimpleWeb::Server<SimpleWeb::HTTP>;
using HttpClient = SimpleWeb::Client<SimpleWeb::HTTP>;

/**
 * The following are a set of wrapper C functions that are registered with the HTTP Server
 * for each of the API entry points. These must be outside if a class as the library has no
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
void readingAppendWrapper(shared_ptr<HttpServer::Response> response,
			  shared_ptr<HttpServer::Request> request)
{
	StorageApi *api = StorageApi::getInstance();
#if WORKER_THREAD_POOL
        api->queue(StorageOperation::ReadingAppend, request, response);
#elif WORKER_THREADS
	std::atomic<int>* cnt = &(api->m_workers_count);
	// Check rurrent number of workers and log if threshold value is hit
	int tVal = std::atomic_load(cnt);
	if (tVal >= MAX_WORKER_THREADS)
	{
		Logger::getLogger()->warn("Storage API: readingAppend() is being run by a new thread. "
					  "Current worker threads count %d exceeds the warning limit of %d allowed threads hit.",
					  tVal,
					  MAX_WORKER_THREADS);
	}

	// Start a new thread
	thread work_thread([api, cnt, response, request]
	{
		// Increase count
		std::atomic_fetch_add(cnt, 1);

		api->readingAppend(response, request);

		// Decrease counter 
		std::atomic_fetch_sub(cnt, 1);
	});
	// Detach the new thread
	work_thread.detach();
#else
	api->readingAppend(response, request);
#endif
}

/**
 * Wrapper function for the reading fetch API call.
 */
void readingFetchWrapper(shared_ptr<HttpServer::Response> response,
			 shared_ptr<HttpServer::Request> request)
{
	StorageApi *api = StorageApi::getInstance();
#if WORKER_THREAD_POOL
        api->queue(StorageOperation::ReadingFetch, request, response);
#elif WORKER_THREADS
	std::atomic<int>* cnt = &(api->m_workers_count);
	// Check rurrent number of workers and log if threshold value is hit
	int tVal = std::atomic_load(cnt);
	if (tVal >= MAX_WORKER_THREADS)
	{
		Logger::getLogger()->warn("Storage API: readingFetch() is being run by a new thread. "
					  "Current worker threads count %d exceeds the warning limit of %d allowed threads hit.",
					  tVal,
					  MAX_WORKER_THREADS);
	}

	// Start a new thread
	thread work_thread([api, cnt, response, request]
	{
		// Increase count
		std::atomic_fetch_add(cnt, 1);

		api->readingFetch(response, request);

		// Decrease counter 
		std::atomic_fetch_sub(cnt, 1);
	});
	// Detach the new thread
	work_thread.detach();
#else
	api->readingFetch(response, request);
#endif
}

/**
 * Wrapper function for the reading query API call.
 */
void readingQueryWrapper(shared_ptr<HttpServer::Response> response,
			 shared_ptr<HttpServer::Request> request)
{
	StorageApi *api = StorageApi::getInstance();
#if WORKER_THREAD_POOL
        api->queue(StorageOperation::ReadingQuery, request, response);
#else
	api->readingQuery(response, request);
#endif
}

/**
 * Wrapper function for the reading purge API call.
 */
void readingPurgeWrapper(shared_ptr<HttpServer::Response> response,
			 shared_ptr<HttpServer::Request> request)
{
	StorageApi *api = StorageApi::getInstance();
#if WORKER_THREAD_POOL
        api->queue(StorageOperation::ReadingPurge, request, response);
#elif WORKER_THREADS
	std::atomic<int>* cnt = &(api->m_workers_count);
	// Check rurrent number of workers and log if threshold value is hit
	int tVal = std::atomic_load(cnt);
	if (tVal >= MAX_WORKER_THREADS)
	{
		Logger::getLogger()->warn("Storage API: readingPurge() is being run by a new thread. "
					  "Current worker threads count %d exceeds the warning limit of %d allowed threads hit.",
					  tVal,
					  MAX_WORKER_THREADS);
	}

	// Start a new thread
	thread work_thread([api, cnt, response, request]
	{
		// Increase count
		std::atomic_fetch_add(cnt, 1);

		api->readingPurge(response, request);
		// Decrease counter 
		std::atomic_fetch_sub(cnt, 1);
	});
	// Detach the new thread
	work_thread.detach();
#else
	api->readingPurge(response, request);
#endif
}

/**
 * Wrapper function for the reading purge API call.
 */
void readingRegisterWrapper(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request)
{
	StorageApi *api = StorageApi::getInstance();
	api->readingRegister(response, request);
}

/**
 * Wrapper function for the reading purge API call.
 */
void readingUnregisterWrapper(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request)
{
	StorageApi *api = StorageApi::getInstance();
	api->readingUnregister(response, request);
}

/**
 * Wrapper function for the table interest register API call.
 */
void tableRegisterWrapper(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request)
{
	StorageApi *api = StorageApi::getInstance();
	api->tableRegister(response, request);
}

/**
 * Wrapper function for the table interest unregister API call.
 */
void tableUnregisterWrapper(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request)
{
	StorageApi *api = StorageApi::getInstance();
	api->tableUnregister(response, request);
}

/**
 * Wrapper function for the create snapshot API call.
 */
void createTableSnapshotWrapper(shared_ptr<HttpServer::Response> response,
				shared_ptr<HttpServer::Request> request)
{
	StorageApi *api = StorageApi::getInstance();
	api->createTableSnapshot(response, request);
}

/**
 * Wrapper function for the load snapshot API call.
 */
void loadTableSnapshotWrapper(shared_ptr<HttpServer::Response> response,
			      shared_ptr<HttpServer::Request> request)
{
	StorageApi *api = StorageApi::getInstance();
	api->loadTableSnapshot(response, request);
}

/**
 * Wrapper function for the delete snapshot API call.
 */
void deleteTableSnapshotWrapper(shared_ptr<HttpServer::Response> response,
				shared_ptr<HttpServer::Request> request)
{
	StorageApi *api = StorageApi::getInstance();
	api->deleteTableSnapshot(response, request);
}

/**
 * Wrapper function for the delete snapshot API call.
 */
void getTableSnapshotsWrapper(shared_ptr<HttpServer::Response> response,
				shared_ptr<HttpServer::Request> request)
{
	StorageApi *api = StorageApi::getInstance();
	api->getTableSnapshots(response, request);
}

/**
 * Wrapper function for the create storage stream API call.
 */
void createStorageStreamWrapper(shared_ptr<HttpServer::Response> response,
				shared_ptr<HttpServer::Request> request)
{
	StorageApi *api = StorageApi::getInstance();
	api->createStorageStream(response, request);
}

/**
 * Wrapper function for the create storage stream API call.
 */
void createStorageSchemaWrapper(shared_ptr<HttpServer::Response> response,
                                shared_ptr<HttpServer::Request> request)
{
        StorageApi *api = StorageApi::getInstance();
        api->createStorageSchema(response, request);
}


/**
 * Wrapper function for the insert into storage table API call.
 */
void storageTableInsertWrapper(shared_ptr<HttpServer::Response> response,
                                shared_ptr<HttpServer::Request> request)
{
        StorageApi *api = StorageApi::getInstance();
        api->storageTableInsert(response, request);
}


/**
 * Wrapper function for the simple query in storage table API call.
 */
void storageTableSimpleQueryWrapper(shared_ptr<HttpServer::Response> response,
                                shared_ptr<HttpServer::Request> request)
{
        StorageApi *api = StorageApi::getInstance();
        api->storageTableSimpleQuery(response, request);
}

/**
 * Wrapper function for the update into storage table API call.
 */
void storageTableUpdateWrapper(shared_ptr<HttpServer::Response> response,
                                shared_ptr<HttpServer::Request> request)
{
        StorageApi *api = StorageApi::getInstance();
        api->storageTableUpdate(response, request);
}

/**
 * Wrapper function for the update into storage table API call.
 */
void storageTableDeleteWrapper(shared_ptr<HttpServer::Response> response,
                                shared_ptr<HttpServer::Request> request)
{
        StorageApi *api = StorageApi::getInstance();
        api->storageTableDelete(response, request);
}

/**
 * Wrapper function for the update into storage table API call.
 */
void storageTableQueryWrapper(shared_ptr<HttpServer::Response> response,
                                shared_ptr<HttpServer::Request> request)
{
        StorageApi *api = StorageApi::getInstance();
        api->storageTableQuery(response, request);
}

/**
 * Construct the singleton Storage API 
 */
StorageApi::StorageApi(const unsigned short port, const unsigned int threads, const unsigned int poolSize) : m_thread(NULL), readingPlugin(0), streamHandler(0)
{
	m_port = port;
	m_threads = threads;
	m_server = new HttpServer();
	m_server->config.port = port;
	m_server->config.thread_pool_size = threads;
	m_server->config.timeout_request = 60;
	m_perfMonitor = NULL;
	m_workerPoolSize = poolSize;
	m_workers.resize(poolSize, NULL);
	StorageApi::m_instance = this;
}

/**
 * Destructor for the storage API class. There is only ever one StorageApi class
 * in existance and it lives for the entire duration of the storage service, so this
 * is really for completeness rather than any pracitical use.
 */
StorageApi::~StorageApi()
{
	if (m_server)
	{
		delete m_server;
	}
	m_instance = NULL;

	if (m_thread)
	{
		delete m_thread;
	}
	if (m_perfMonitor)
	{
		delete m_perfMonitor;
	}
	for (unsigned int i = 0; i < m_workerPoolSize; i++)
	{
		if (m_workers[i])
			delete m_workers[i];
	}
}

/**
 * Return the singleton instance of the StorageAPI class
 */
StorageApi *StorageApi::getInstance()
{
	if (m_instance == NULL)
	{
		Logger::getLogger()->warn("Creating a default storage API instance, tuning parameters will be ignored");
		m_instance = new StorageApi(0, 1, 5);
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
	// Initialise workers threads counter
	m_workers_count = ATOMIC_VAR_INIT(0);

	// Initialise the API entry points
	m_server->resource[COMMON_ACCESS]["POST"] = commonInsertWrapper;
	m_server->resource[COMMON_ACCESS]["GET"] = commonSimpleQueryWrapper;
	m_server->resource[COMMON_QUERY]["PUT"] = commonQueryWrapper;
	m_server->resource[COMMON_ACCESS]["PUT"] = commonUpdateWrapper;
	m_server->resource[COMMON_ACCESS]["DELETE"] = commonDeleteWrapper;
	m_server->default_resource["POST"] = defaultWrapper;
	m_server->default_resource["PUT"] = defaultWrapper;
	m_server->default_resource["GET"] = defaultWrapper;
	m_server->default_resource["DELETE"] = defaultWrapper;

	m_server->resource[READING_INTEREST]["POST"] = readingRegisterWrapper;
	m_server->resource[READING_INTEREST]["DELETE"] = readingUnregisterWrapper;

	m_server->resource[TABLE_INTEREST]["POST"] = tableRegisterWrapper;
	m_server->resource[TABLE_INTEREST]["DELETE"] = tableUnregisterWrapper;

	m_server->resource[CREATE_TABLE_SNAPSHOT]["POST"] = createTableSnapshotWrapper;
	m_server->resource[LOAD_TABLE_SNAPSHOT]["PUT"] = loadTableSnapshotWrapper;
	m_server->resource[DELETE_TABLE_SNAPSHOT]["DELETE"] = deleteTableSnapshotWrapper;
	m_server->resource[GET_TABLE_SNAPSHOTS]["GET"] = getTableSnapshotsWrapper;

	m_server->resource[READING_ACCESS]["POST"] = readingAppendWrapper;
	m_server->resource[READING_ACCESS]["GET"] = readingFetchWrapper;
	m_server->resource[READING_QUERY]["PUT"] = readingQueryWrapper;
	m_server->resource[READING_PURGE]["PUT"] = readingPurgeWrapper;

	m_server->resource[CREATE_STORAGE_STREAM]["POST"] = createStorageStreamWrapper;
	m_server->resource[STORAGE_SCHEMA]["POST"] = createStorageSchemaWrapper;

	m_server->resource[STORAGE_TABLE_ACCESS]["POST"] = storageTableInsertWrapper;
	m_server->resource[STORAGE_TABLE_ACCESS]["GET"] = storageTableSimpleQueryWrapper;
	m_server->resource[STORAGE_TABLE_ACCESS]["PUT"] = storageTableUpdateWrapper;
	m_server->resource[STORAGE_TABLE_ACCESS]["DELETE"] = storageTableDeleteWrapper;
	m_server->resource[STORAGE_TABLE_QUERY]["PUT"] = storageTableQueryWrapper;

	m_server->on_error = on_error;

	ManagementApi *management = ManagementApi::getInstance();
	management->registerStats(&stats);

	// Create StoragePerformanceMonitor object fr direct monitorind data saving
	m_perfMonitor = new StoragePerformanceMonitor("Storage", this);
}

void startService()
{
	StorageApi::getInstance()->startServer();
}


/**
 * Static method used to start the thread
 */
static void workerStart()
{
	StorageApi *api = StorageApi::getInstance();
	api->worker();
}

/**
 * Start the HTTP server
 */
void StorageApi::start() {
	m_thread = new thread(startService);
	m_shutdown = false;
	for (unsigned int i = 0; i < m_workerPoolSize; i++)
	{
		m_workers[i] = new thread(workerStart);
	}
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
	m_shutdown = true;
	m_queueCV.notify_all();
	for (unsigned int i = 0; i < m_workerPoolSize; i++)
	{
		if (m_workers[i])
		{
			m_workers[i]->join();
			delete m_workers[i];
			m_workers[i] = NULL;
		}
	}
}

/**
 * Connect with the storage plugin
 */
void StorageApi::setPlugin(StoragePlugin *plugin)
{
	this->plugin = plugin;
}

/**
 * Connect with the storage plugin
 */
void StorageApi::setReadingPlugin(StoragePlugin *plugin)
{
	this->readingPlugin = plugin;
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
 * The worker thread
 */
void StorageApi::worker()
{
	unique_lock<mutex> lck(m_queueMutex);
	while (!m_shutdown)
	{
		while (!m_queue.empty())
		{
			StorageOperation *op = m_queue.front();
			m_queue.pop();
			lck.unlock();
			switch (op->m_operation)
			{
			case StorageOperation::ReadingAppend:
				readingAppend(op->m_response, op->m_request);
				break;
			case StorageOperation::ReadingFetch:
				readingFetch(op->m_response, op->m_request);
				break;
			case StorageOperation::ReadingPurge:
				readingPurge(op->m_response, op->m_request);
				break;
			case StorageOperation::ReadingQuery:
				readingQuery(op->m_response, op->m_request);
				break;
			default:
				Logger::getLogger()->error("Internal error, unknown operation %d requested of storage worker thread", op->m_operation);
				break;
			}
			delete op;
			lck.lock();
		}
		m_queueCV.wait(lck);
	}
}

/**
 * Append a request to the readings request queue
 *
 * If the queue is starting to get long delay the return as
 * a primitive way to throttle incoming requests
 *
 * @param op	The operation to perform
 * @param request	The HTTP request
 * @param response	The HTTP response
 */
void StorageApi::queue(StorageOperation::Operations op, shared_ptr<HttpServer::Request> request, shared_ptr<HttpServer::Response> response)
{
	unique_lock<mutex> lck(m_queueMutex);
	m_queue.push(new StorageOperation(op, request, response));
	m_queueCV.notify_all();
	unsigned int length = m_queue.size();
	m_perfMonitor->collect("Worker Queue length", length);
	if (length > 10)
	{
		lck.unlock();
		usleep(1000 * length);
		if (length % 10 == 0)
			Logger::getLogger()->warn("Reading request queue now at %d", length);
	}
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
			registry.processTableInsert(tableName, payload);
			responsePayload = "{ \"response\" : \"inserted\", \"rows_affected\" : ";
			responsePayload += to_string(rval);
			responsePayload += " }";
			respond(response, responsePayload);

			if (m_perfMonitor->isCollecting())
			{
				m_perfMonitor->collect("insert rows " + tableName, rval);
				m_perfMonitor->collect("insert Payload Size " + tableName, payload.length());
			}
		}
		else
		{
			mapError(responsePayload, plugin->lastError());
			respond(response, SimpleWeb::StatusCode::client_error_bad_request, responsePayload);
		}
	} catch (exception& ex) {
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

	auto header_seq = request->header.find("SeqNum");
	if(header_seq != request->header.end())
	{
		string threadId = header_seq->second.substr(0, header_seq->second.find("_"));
		int seqNum = stoi(header_seq->second.substr(header_seq->second.find("_")+1));
		{
			std::unique_lock<std::mutex> lock(mtx_seqnum_map);
			auto it = m_seqnum_map.find(threadId);
			if (it != m_seqnum_map.end())
			{
				if (seqNum <= it->second.first)
				{
					responsePayload = "{ \"response\" : \"updated\", \"rows_affected\"  : ";
					responsePayload += to_string(0);
					responsePayload += " }";
					Logger::getLogger()->info("%s:%d: Repeat/old request: responding with zero response - threadId=%s, last seen seqNum for this threadId=%d, HTTP request header seqNum=%d",
									__FUNCTION__, __LINE__, threadId.c_str(), it->second.first, seqNum);
					respond(response, responsePayload);
					return;
				}
				
				// remove this threadId from LRU list; will add this to front of LRU list below
				seqnum_map_lru_list.erase(m_seqnum_map[threadId].second);
			}
			else
			{
				if (seqnum_map_lru_list.size() == max_entries_in_seqnum_map) // LRU list is full
				{
					//delete least recently used element
					string last = seqnum_map_lru_list.back();
					seqnum_map_lru_list.pop_back();
					m_seqnum_map.erase(last);
				}
			}

			// insert an entry for threadId at front of LRU queue
			seqnum_map_lru_list.push_front(threadId);
			m_seqnum_map[threadId] = make_pair(seqNum, seqnum_map_lru_list.begin());
		}
	}
	
	stats.commonUpdate++;
	try {
		tableName = request->path_match[TABLE_NAME_COMPONENT];
		payload = request->content.string();

		int rval = plugin->commonUpdate(tableName, payload);
		if (rval != -1)
		{
			registry.processTableUpdate(tableName, payload);
			responsePayload = "{ \"response\" : \"updated\", \"rows_affected\"  : ";
			responsePayload += to_string(rval);
			responsePayload += " }";
			respond(response, responsePayload);

			if (m_perfMonitor->isCollecting())
			{
				m_perfMonitor->collect("update rows " + tableName, rval);
				m_perfMonitor->collect("update Payload Size " + tableName, payload.length());
			}
		}
		else
		{
			mapError(responsePayload, plugin->lastError());
			respond(response, SimpleWeb::StatusCode::client_error_bad_request, responsePayload);
		}

	} catch (exception& ex) {
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
	} catch (exception& ex) {
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

	} catch (exception& ex) {
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
			registry.processTableDelete(tableName, payload);
			responsePayload = "{ \"response\" : \"deleted\", \"rows_affected\"  : ";
			responsePayload += to_string(rval);
			responsePayload += " }";
			respond(response, responsePayload);

			if (m_perfMonitor->isCollecting())
			{
				m_perfMonitor->collect("delete rows " + tableName, rval);
				m_perfMonitor->collect("delete Payload Size " + tableName, payload.length());
			}
		}
		else
		{
			mapError(responsePayload, plugin->lastError());
			respond(response, SimpleWeb::StatusCode::client_error_bad_request, responsePayload);
		}

	} catch (exception& ex) {
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
struct timeval	tStart, tEnd;

	if (m_perfMonitor->isCollecting())
	{
		gettimeofday(&tStart, NULL);
	}
	
	auto header_seq = request->header.find("SeqNum");
	if(header_seq != request->header.end())
	{
		string threadId = header_seq->second.substr(0, header_seq->second.find("_"));
		int seqNum = stoi(header_seq->second.substr(header_seq->second.find("_")+1));

		{
			std::unique_lock<std::mutex> lock(mtx_seqnum_map);
			auto it = m_seqnum_map.find(threadId);
			if (it != m_seqnum_map.end())
			{
				if (seqNum <= it->second.first)
				{
					responsePayload = "{ \"response\" : \"appended\", \"readings_added\" : ";
					responsePayload += to_string(0);
					responsePayload += " }";
					Logger::getLogger()->info("%s:%d: Repeat/old request: responding with zero response - threadId=%s, last seen seqNum for this threadId=%d, HTTP request header seqNum=%d",
									__FUNCTION__, __LINE__, threadId.c_str(), it->second.first, seqNum);
					respond(response, responsePayload);
					return;
				}
				// remove this threadId from LRU list; will add this to front of LRU list below
				seqnum_map_lru_list.erase(m_seqnum_map[threadId].second);
			}
			else
			{
				if (seqnum_map_lru_list.size() == max_entries_in_seqnum_map) // LRU list is full
				{
					//delete least recently used element
					string last = seqnum_map_lru_list.back();
					seqnum_map_lru_list.pop_back();
					m_seqnum_map.erase(last);
				}
			}
			// insert an entry for threadId at front of LRU queue
			seqnum_map_lru_list.push_front(threadId);
			m_seqnum_map[threadId] = make_pair(seqNum, seqnum_map_lru_list.begin());
		}
	}

	stats.readingAppend++;
	try {
		payload = request->content.string();
		int rval = (readingPlugin ? readingPlugin : plugin)->readingsAppend(payload);
		if (rval != -1)
		{
			registry.process(payload);
			responsePayload = "{ \"response\" : \"appended\", \"readings_added\" : ";
			responsePayload += to_string(rval);
			responsePayload += " }";
			respond(response, responsePayload);

			if (m_perfMonitor->isCollecting())
			{
				gettimeofday(&tEnd, NULL);
				m_perfMonitor->collect("Reading Append Rows " +
						(readingPlugin ? readingPlugin : plugin)->getName(),
						rval);
				m_perfMonitor->collect("Reading Append PayloadSize " +
						(readingPlugin ? readingPlugin : plugin)->getName(),
						payload.length());
				struct timeval diff;
				timersub(&tEnd, &tStart, &diff);
				m_perfMonitor->collect("Reading Append Time (ms)", diff.tv_sec * 1000 + diff.tv_usec / 1000);
			}
		}
		else
		{
			mapError(responsePayload, (readingPlugin ? readingPlugin : plugin)->lastError());
			respond(response, SimpleWeb::StatusCode::client_error_bad_request, responsePayload);
		}

		//respond(response, responsePayload);
	} catch (exception& ex) {
		internalError(response, ex);
	}
}

/**
 * Fetch a block of readings.
 *
 * @param response	The response stream to send the response on
 * @param request	The HTTP request
 */
void StorageApi::readingFetch(shared_ptr<HttpServer::Response> response,
			      shared_ptr<HttpServer::Request> request)
{
SimpleWeb::CaseInsensitiveMultimap query;
unsigned long			   id = 0;
unsigned long			   count = 0;
	stats.readingFetch++;
	try {
		query = request->parse_query_string();

		auto search = query.find("id");
		if (search == query.end())
		{
			string payload = "{ \"error\" : \"Missing query parameter id\" }";
			respond(response,
				SimpleWeb::StatusCode::client_error_bad_request,
				payload);
			return;
		}
		else
		{
			id = (unsigned long)atol(search->second.c_str());
		}
		search = query.find("count");
		if (search == query.end())
		{
			string payload = "{ \"error\" : \"Missing query parameter count\" }";
			respond(response,
				SimpleWeb::StatusCode::client_error_bad_request,
				payload);
			return;
		}
		else
		{
			count = (unsigned)atol(search->second.c_str());
		}

		// Get plugin data
		char *responsePayload = (readingPlugin ? readingPlugin : plugin)->readingsFetch(id, count);
		string res = responsePayload;

		// Reply to client
		respond(response, res);
		// Free plugin data
		free(responsePayload);
	} catch (exception& ex) {
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

		char *resultSet = (readingPlugin ? readingPlugin : plugin)->readingsRetrieve(payload);
		string res = resultSet;

		respond(response, res);
		free(resultSet);
	} catch (exception& ex) {
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
string	      asset;
bool	      byAsset = false;
static std::atomic<bool> already_running(false);

	if (already_running)
	{
		string payload = "{ \"error\" : \"Previous instance of purge is still running, not starting another one.\" }";
		respond(response, SimpleWeb::StatusCode::client_error_too_many_requests, payload);
		return;
	}
	already_running.store(true);
		
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
		search = query.find("asset");
		if (search != query.end())
		{
			asset = search->second;
			byAsset = true;
		}
		search = query.find("sent");
		if (search == query.end())
		{
			if (!byAsset)
			{
				string payload = "{ \"error\" : \"Missing query parameter sent\" }";
				respond(response, SimpleWeb::StatusCode::client_error_bad_request, payload);
				already_running.store(false);
				return;
			}
		}
		else
		{
			lastSent = (unsigned)atol(search->second.c_str());
		}

		search = query.find("flags");

		if (search != query.end())
		{
			flags = search->second;

			Logger::getLogger()->debug("%s - flags :%s:", __FUNCTION__, flags.c_str());

			// TODO Turn flags into a bitmap

			if (flags.compare(PURGE_FLAG_RETAIN_ANY) == 0)
			{

				flagsMask |= STORAGE_PURGE_RETAIN_ANY;
			}
			else if ( (flags.compare(PURGE_FLAG_RETAIN)     == 0) ||  // Backward compability
			         (flags.compare(PURGE_FLAG_RETAIN_ALL) == 0) )
			{
				flagsMask |= STORAGE_PURGE_RETAIN_ALL;
			}
			else if (flags.compare(PURGE_FLAG_PURGE) == 0)
			{
				flagsMask &= (~STORAGE_PURGE_RETAIN_ANY);
				flagsMask &= (~STORAGE_PURGE_RETAIN_ALL);
			}

			Logger::getLogger()->debug("%s - flagsMask :%d:", __FUNCTION__, flagsMask);

		}


		char *purged = NULL;
		if (age)
		{
			purged = (readingPlugin ? readingPlugin : plugin)->readingsPurge(age, flagsMask, lastSent);
		}
		else if (size)
		{
			purged = (readingPlugin ? readingPlugin : plugin)->readingsPurge(size, flagsMask|STORAGE_PURGE_SIZE, lastSent);
		}
		else if (byAsset)
		{
			purged = (readingPlugin ? readingPlugin : plugin)->readingsPurgeAsset(asset);
		}
		else
		{
			string payload = "{ \"error\" : \"Must either specify age or size parameter\" }";
			respond(response, SimpleWeb::StatusCode::client_error_bad_request, payload);
			already_running.store(false);
			return;
		}
		respond(response, purged);
		free(purged);
	}
	/** Handle PluginNotImplementedException exception here */
	catch (PluginNotImplementedException& ex) {
		string payload = "{ \"error\" : \"";
		payload += ex.what();
		payload += "\" }";
		/** Return HTTP code 400 with message from storage plugin */
		respond(response, SimpleWeb::StatusCode::client_error_bad_request, payload);
		already_running.store(false);
		return;
	}
	/** Handle general exception */
	catch (exception& ex) {
		internalError(response, ex);
		already_running.store(false);
		return;
	}
	already_running.store(false);
}

/**
 * Register interest in readings for an asset
 */
void StorageApi::readingRegister(shared_ptr<HttpServer::Response> response,
				 shared_ptr<HttpServer::Request> request)
{
string		asset;
string		payload;
Document	doc;

	payload = request->content.string();
	// URL decode asset name
	asset = urlDecode(request->path_match[ASSET_NAME_COMPONENT]);
	doc.Parse(payload.c_str());
	if (doc.HasParseError())
	{
			string resp = "{ \"error\" : \"Badly formed payload\" }";
			respond(response,
				SimpleWeb::StatusCode::client_error_bad_request,
				resp);
	}
	else
	{
		if (doc.HasMember("url"))
		{
			registry.registerAsset(asset, doc["url"].GetString());
			string resp = " { \"" + asset + "\" : \"registered\" }";
			respond(response, resp);
		}
		else
		{
			string resp = "{ \"error\" : \"Missing url element in payload\" }";
			respond(response, SimpleWeb::StatusCode::client_error_bad_request, resp);
		}
	}
}

/**
 * Unregister interest in readings for an asset
 */
void StorageApi::readingUnregister(shared_ptr<HttpServer::Response> response,
				   shared_ptr<HttpServer::Request> request)
{
string		asset;
string		payload;
Document	doc;

	payload = request->content.string();
	// URL decode asset name
	asset = urlDecode(request->path_match[ASSET_NAME_COMPONENT]);
	doc.Parse(payload.c_str());
	if (doc.HasParseError())
	{
			string resp = "{ \"error\" : \"Badly formed payload\" }";
			respond(response,
				SimpleWeb::StatusCode::client_error_bad_request,
				resp);
	}
	else
	{
		if (doc.HasMember("url"))
		{
			registry.unregisterAsset(asset, doc["url"].GetString());
			string resp = " { \"" + asset + "\" : \"unregistered\" }";
			respond(response, resp);
		}
		else
		{
			string resp = "{ \"error\" : \"Missing url element in payload\" }";
			respond(response,
				SimpleWeb::StatusCode::client_error_bad_request,
				resp);
		}
	}
}

/**
 * Register interest in readings for an asset
 */
void StorageApi::tableRegister(shared_ptr<HttpServer::Response> response,
				 shared_ptr<HttpServer::Request> request)
{
string		table;
string		payload;
Document	doc;

	payload = request->content.string();
	// URL decode table name
	table = urlDecode(request->path_match[TABLE_NAME_COMPONENT]);
	
	doc.Parse(payload.c_str());
	if (doc.HasParseError())
	{
		string resp = "{ \"error\" : \"Badly formed payload\" }";
		respond(response,
			SimpleWeb::StatusCode::client_error_bad_request,
			resp);
	}
	else
	{
		if (doc.HasMember("url"))
		{
			registry.registerTable(table, payload);
			string resp = " { \"" + table + "\" : \"registered\" }";
			respond(response, resp);
		}
		else
		{
			string resp = "{ \"error\" : \"Missing url element in payload\" }";
			respond(response, SimpleWeb::StatusCode::client_error_bad_request, resp);
		}
	}
}

/**
 * Unregister interest in readings for an asset
 */
void StorageApi::tableUnregister(shared_ptr<HttpServer::Response> response,
				   shared_ptr<HttpServer::Request> request)
{
string		table;
string		payload;
Document	doc;

	payload = request->content.string();
	// URL decode table name
	table = urlDecode(request->path_match[TABLE_NAME_COMPONENT]);
	
	doc.Parse(payload.c_str());
	if (doc.HasParseError())
	{
			string resp = "{ \"error\" : \"Badly formed payload\" }";
			respond(response,
				SimpleWeb::StatusCode::client_error_bad_request,
				resp);
	}
	else
	{
		if (doc.HasMember("url"))
		{
			registry.unregisterTable(table, payload);
			string resp = " { \"" + table + "\" : \"unregistered\" }";
			respond(response, resp);
		}
		else
		{
			string resp = "{ \"error\" : \"Missing url element in payload\" }";
			respond(response, SimpleWeb::StatusCode::client_error_bad_request, resp);
		}
	}
}

/**
 * Create a stream for high speed storage ingestion
 *
 * @param response	The response stream to send the response on
 * @param request	The HTTP request
 */
void StorageApi::createStorageStream(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request)
{
string	responsePayload;

	(void)(request); 	// Surpress unused arguemnt warning
	try {
		if (!streamHandler)
		{
			streamHandler = new StreamHandler(this);
		}
		uint32_t token;
		uint32_t port = streamHandler->createStream(&token);
		if (port != 0)
		{
			responsePayload = "{ \"port\":"; 
			responsePayload += to_string(port);
			responsePayload += ", \"token\":"; 
			responsePayload += to_string(token);
			responsePayload += " }";
			respond(response, responsePayload);
		}
		else
		{
			respond(response, SimpleWeb::StatusCode::client_error_bad_request, responsePayload);
		}

	} catch (exception& ex) {
		internalError(response, ex);
		}
}

/**
 * Append the readings that have arrived via a stream to the storage plugin
 *
 * @param readings	A Null terminated array of points to ReadingStream structures
 * @param commit	A flag to commit the readings block
 */
bool StorageApi::readingStream(ReadingStream **readings, bool commit)
{
	if ((readingPlugin ? readingPlugin : plugin)->hasStreamSupport())
	{
		return (readingPlugin ? readingPlugin : plugin)->readingStream(readings, commit);
	}
	else
	{
		// Plugin does not support streaming input
		ostringstream convert;
		char	ts[60], micro_s[10];
		

		convert << "{\"readings\":[";
		for (int i = 0; readings[i]; i++)
		{
			if (i > 0)
				convert << ",";
			convert << "{\"asset_code\":\"";
			convert << readings[i]->assetCode;
			convert << "\",\"user_ts\":\"";
			struct tm timeinfo;
			gmtime_r(&readings[i]->userTs.tv_sec, &timeinfo);
			std::strftime(ts, sizeof(ts), "%Y-%m-%d %H:%M:%S", &timeinfo);
			snprintf(micro_s, sizeof(micro_s), ".%06lu", readings[i]->userTs.tv_usec);
			convert << ts << micro_s;
			convert << "\",\"reading\":";
			convert << &(readings[i]->assetCode[readings[i]->assetCodeLength]);
			convert << "}";
		}
		convert << "]}";
		Logger::getLogger()->debug("Fallback created payload: %s", convert.str().c_str());
		(readingPlugin ? readingPlugin : plugin)->readingsAppend(convert.str());
	}	
	return false;
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
		if (*ptr1 == '\n')
			ptr1++;
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

/**
 * Create a table snapshot
 */
void StorageApi::createTableSnapshot(shared_ptr<HttpServer::Response> response,
				     shared_ptr<HttpServer::Request> request)
{
string   sTable;
string   payload;
Document doc;

	payload = request->content.string();
	sTable = request->path_match[TABLE_NAME_COMPONENT];
	doc.Parse(payload.c_str());
	if (!doc.HasMember("id"))
	{
		string resp = "{ \"error\" : \"Missing id element in payload for create snapshot\" }";
		respond(response, SimpleWeb::StatusCode::client_error_bad_request, resp);
		return;
	}

	string responsePayload;
	string sId = doc["id"].GetString();
	// call plugin method
	if (plugin->createTableSnapshot(sTable, sId) < 0)
	{
		mapError(responsePayload, plugin->lastError());
		respond(response,
			SimpleWeb::StatusCode::client_error_bad_request,
			responsePayload);
	}
	else
	{
		responsePayload = "{\"created\": {\"id\": \"" + sId;
		responsePayload += "\", \"table\": \"" + sTable + "\"} }";
		respond(response, responsePayload);
	}
}

/**
 * Load a table snapshot
 */
void StorageApi::loadTableSnapshot(shared_ptr<HttpServer::Response> response,
				     shared_ptr<HttpServer::Request> request)
{
string   sId;
string   sTable;
string   payload;

	payload = request->content.string();
	sTable = request->path_match[TABLE_NAME_COMPONENT];
	sId = request->path_match[SNAPSHOT_ID_COMPONENT];
	if (sId.empty())
	{
		string resp = "{ \"error\" : \"Missing id element in payload for load snapshot\" }";
		respond(response, SimpleWeb::StatusCode::client_error_bad_request, resp);
		return;
	}
	string responsePayload;
	if (plugin->loadTableSnapshot(sTable, sId) < 0)
	{
		mapError(responsePayload, plugin->lastError());
		respond(response,
			SimpleWeb::StatusCode::client_error_bad_request,
			responsePayload);
	}
	else
	{
		responsePayload = "{\"loaded\": {\"id\": \"" + sId;
		responsePayload += "\", \"table\": \"" + sTable + "\"} }";
		respond(response, responsePayload);
	}
}

/**
 * Delete a table snapshot
 */
void StorageApi::deleteTableSnapshot(shared_ptr<HttpServer::Response> response,
				     shared_ptr<HttpServer::Request> request)
{
string   sId;
string   sTable;
string   payload;

	payload = request->content.string();
	sTable = request->path_match[TABLE_NAME_COMPONENT];
	sId = request->path_match[SNAPSHOT_ID_COMPONENT];
	if (sId.empty())
	{
		string resp = "{ \"error\" : \"Missing id element in payload fopr delete snapshot\" }";
		respond(response, SimpleWeb::StatusCode::client_error_bad_request, resp);
		return;
	}
	string responsePayload;
	if (plugin->deleteTableSnapshot(sTable, sId) < 0)
	{
		mapError(responsePayload, plugin->lastError());
		respond(response,
			SimpleWeb::StatusCode::client_error_bad_request,
			responsePayload);
	}
	else
	{
		responsePayload = "{\"deleted\": {\"id\": \"" + sId;
		responsePayload += "\", \"table\": \"" + sTable + "\"} }";
		respond(response, responsePayload);
	}
}

/**
 * Get list of a table snapshots
 */
void StorageApi::getTableSnapshots(shared_ptr<HttpServer::Response> response,
				   shared_ptr<HttpServer::Request> request)
{
string   sTable;
string   payload;

        try
	{
		payload = request->content.string();
		sTable = request->path_match[TABLE_NAME_COMPONENT];

		// Get plugin data
                char* pluginResult = plugin->getTableSnapshots(sTable);
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
			respond(response,
				SimpleWeb::StatusCode::client_error_bad_request,
				responsePayload);
		}
        } catch (exception& ex) {
                internalError(response, ex);
        }
}


/**
 * Perform an create table and create index for schema provided in the payload.
 *
 * @param response      The response stream to send the response on
 * @param request       The HTTP request
 */
void StorageApi::createStorageSchema(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request)
{
string  payload;
string  responsePayload;

        try {
                payload = request->content.string();

                int rval = plugin->createSchema(payload);
                if (rval != -1)
                {
                        responsePayload = "{ \"Successfully created schema\"}  ";
                        respond(response, responsePayload);
                }
                else
                {
                        mapError(responsePayload, plugin->lastError());
                        respond(response, SimpleWeb::StatusCode::client_error_bad_request, responsePayload);
                }

        } catch (exception& ex) {
                internalError(response, ex);
        }
}

/**
 * Perform an insert table operation.
 *
 * @param response      The response stream to send the response on
 * @param request       The HTTP request
 */
void StorageApi::storageTableInsert(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request)
{
string  schemaName;
string  tableName;
string  payload;
string  responsePayload;

        stats.commonInsert++;
        try {
		schemaName = request->path_match[STORAGE_SCHEMA_NAME_COMPONENT];
                tableName = request->path_match[STORAGE_TABLE_NAME_COMPONENT];
                payload = request->content.string();

                int rval = plugin->commonInsert(tableName, payload, const_cast<char*>(schemaName.c_str()));
                if (rval != -1)
                {
			if (m_perfMonitor->isCollecting())
			{
				m_perfMonitor->collect("insert rows " + tableName, rval);
				m_perfMonitor->collect("insert Payload Size " + tableName, payload.length());
			}
			registry.processTableInsert(tableName, payload);
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
        } catch (exception& ex) {
                internalError(response, ex);
        }
}

/**
 * Perform an update on a table of the data provided in the payload.
 *
 * @param response      The response stream to send the response on
 * @param request       The HTTP request
 */
void StorageApi::storageTableUpdate(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request)
{
string  schemaName;
string  tableName;
string  payload;
string  responsePayload;

        auto header_seq = request->header.find("SeqNum");
        if(header_seq != request->header.end())
        {
                string threadId = header_seq->second.substr(0, header_seq->second.find("_"));
                int seqNum = stoi(header_seq->second.substr(header_seq->second.find("_")+1));
                {
                        std::unique_lock<std::mutex> lock(mtx_seqnum_map);
                        auto it = m_seqnum_map.find(threadId);
                        if (it != m_seqnum_map.end())
                        {
                                if (seqNum <= it->second.first)
                                {
                                        responsePayload = "{ \"response\" : \"updated\", \"rows_affected\"  : ";
                                        responsePayload += to_string(0);
                                        responsePayload += " }";
                                        Logger::getLogger()->info("%s:%d: Repeat/old request: responding with zero response - threadId=%s, last seen seqNum for this threadId=%d, HTTP request header seqNum=%d",
                                                                        __FUNCTION__, __LINE__, threadId.c_str(), it->second.first, seqNum);
                                        respond(response, responsePayload);
                                        return;
				}

                                // remove this threadId from LRU list; will add this to front of LRU list below
                                seqnum_map_lru_list.erase(m_seqnum_map[threadId].second);
                        }
                        else
                        {
                                if (seqnum_map_lru_list.size() == max_entries_in_seqnum_map) // LRU list is full
                                {
                                        //delete least recently used element
                                        string last = seqnum_map_lru_list.back();
                                        seqnum_map_lru_list.pop_back();
                                        m_seqnum_map.erase(last);
                                }
                        }

                        // insert an entry for threadId at front of LRU queue
                        seqnum_map_lru_list.push_front(threadId);
                        m_seqnum_map[threadId] = make_pair(seqNum, seqnum_map_lru_list.begin());
                }
        }

        stats.commonUpdate++;
        try {
		schemaName = request->path_match[STORAGE_SCHEMA_NAME_COMPONENT];
                tableName = request->path_match[STORAGE_TABLE_NAME_COMPONENT];
                payload = request->content.string();

                int rval = plugin->commonUpdate(tableName, payload, const_cast<char*>(schemaName.c_str()));
                if (rval != -1)
                {
			if (m_perfMonitor->isCollecting())
			{
				m_perfMonitor->collect("update rows " + tableName, rval);
				m_perfMonitor->collect("update Payload Size " + tableName, payload.length());
			}
			registry.processTableUpdate(tableName, payload);
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

        } catch (exception& ex) {
                internalError(response, ex);
                }
}

/**
 * Perform a delete on a table using the condition encoded in the JSON payload
 *
 * @param response      The response stream to send the response on
 * @param request       The HTTP request
 */
void StorageApi::storageTableDelete(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request)
{
string 	schemaName;
string  tableName;
string  payload;
string  responsePayload;

        stats.commonDelete++;
        try {
		schemaName = request->path_match[STORAGE_SCHEMA_NAME_COMPONENT];
                tableName = request->path_match[STORAGE_TABLE_NAME_COMPONENT];
                payload = request->content.string();

                int rval = plugin->commonDelete(tableName, payload, const_cast<char*>(schemaName.c_str()));
                if (rval != -1)
                {
			if (m_perfMonitor->isCollecting())
			{
				m_perfMonitor->collect("delete rows " + tableName, rval);
				m_perfMonitor->collect("delete Payload Size " + tableName, payload.length());
			}
			registry.processTableDelete(tableName, payload);
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

	}catch (exception& ex) {
               	internalError(response, ex);
        }
}

/**
 * Perform a simple query on the table using the query parameters as conditions
 * TODO make this work for multiple column queries
 *
 * @param response      The response stream to send the response on
 * @param request       The HTTP request
 */
void StorageApi::storageTableSimpleQuery(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request)
{
string  schemaName;
string  tableName;
SimpleWeb::CaseInsensitiveMultimap      query;
string payload;

        stats.commonSimpleQuery++;
        try {
		schemaName = request->path_match[STORAGE_SCHEMA_NAME_COMPONENT];
                tableName = request->path_match[STORAGE_TABLE_NAME_COMPONENT];
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
                char *pluginResult = plugin->commonRetrieve(tableName, payload, const_cast<char*>(schemaName.c_str()));
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
        } catch (exception& ex) {
                internalError(response, ex);
        }
}

/**
 * Perform query on a table using the JSON encoded query in the payload
 *
 * @param response      The response stream to send the response on
 * @param request       The HTTP request
 */
void StorageApi::storageTableQuery(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request)
{
string  schemaName;
string  tableName;
string  payload;

        stats.commonQuery++;
        try {
		schemaName = request->path_match[STORAGE_SCHEMA_NAME_COMPONENT];
                tableName = request->path_match[STORAGE_TABLE_NAME_COMPONENT];
                payload = request->content.string();

                char *pluginResult = plugin->commonRetrieve(tableName, payload, const_cast<char*>(schemaName.c_str()));
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

        } catch (exception& ex) {
                internalError(response, ex); 
        }
}

