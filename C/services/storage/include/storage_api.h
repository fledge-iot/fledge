#ifndef _STORAGE_API_H
#define _STORAGE_API_H
/*
 * Fledge storage service.
 *
 * Copyright (c) 2017 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch, Massimiliano Pinto
 */

#include <server_http.hpp>
#include <storage_plugin.h>
#include <storage_stats.h>
#include <storage_registry.h>
#include <stream_handler.h>
#include <perfmonitors.h>

using namespace std;
using HttpServer = SimpleWeb::Server<SimpleWeb::HTTP>;

/*
 * The URL for each entry point
 */
#define COMMON_ACCESS		"^/storage/table/([A-Za-z][a-zA-Z0-9_]*)$"
#define COMMON_QUERY		"^/storage/table/([A-Za-z][a-zA-Z_0-9]*)/query$"
#define READING_ACCESS  	"^/storage/reading$"
#define READING_QUERY   	"^/storage/reading/query"
#define READING_PURGE   	"^/storage/reading/purge"
#define READING_INTEREST	"^/storage/reading/interest/([A-Za-z0-9\\*][a-zA-Z0-9_%\\.\\-]*)$"
#define TABLE_INTEREST		"^/storage/table/interest/([A-Za-z\\*][a-zA-Z0-9_%\\.\\-]*)$"

#define GET_TABLE_SNAPSHOTS	"^/storage/table/([A-Za-z][a-zA-Z_0-9_]*)/snapshot$"
#define CREATE_TABLE_SNAPSHOT	GET_TABLE_SNAPSHOTS
#define LOAD_TABLE_SNAPSHOT	"^/storage/table/([A-Za-z][a-zA-Z_0-9_]*)/snapshot/([a-zA-Z_0-9_]*)$"
#define DELETE_TABLE_SNAPSHOT	LOAD_TABLE_SNAPSHOT
#define CREATE_STORAGE_STREAM	"^/storage/reading/stream$"
#define STORAGE_SCHEMA		"^/storage/schema"
#define STORAGE_TABLE_ACCESS    "^/storage/schema/([A-Za-z][a-zA-Z0-9_]*)/table/([A-Za-z][a-zA-Z0-9_]*)$"
#define STORAGE_TABLE_QUERY	 "^/storage/schema/([A-Za-z][a-zA-Z0-9_]*)/table/([A-Za-z][a-zA-Z_0-9]*)/query$"           

#define PURGE_FLAG_RETAIN      "retain"
#define PURGE_FLAG_RETAIN_ANY  "retainany"
#define PURGE_FLAG_RETAIN_ALL  "retainall"
#define PURGE_FLAG_PURGE       "purge"

#define TABLE_NAME_COMPONENT	1
#define STORAGE_SCHEMA_NAME_COMPONENT	1
#define STORAGE_TABLE_NAME_COMPONENT	2
#define ASSET_NAME_COMPONENT	1
#define SNAPSHOT_ID_COMPONENT	2

/**
 * Class used to queue the operations to be executed by
 * the worker thread pool
 */
class StorageOperation {
	public:
		enum Operations	{ ReadingAppend, ReadingPurge, ReadingFetch, ReadingQuery };
	public:
		StorageOperation(StorageOperation::Operations operation, shared_ptr<HttpServer::Request> request,
				shared_ptr<HttpServer::Response> response) :
					m_operation(operation),
					m_request(request),
					m_response(response)
		{
		};
		~StorageOperation()
		{
		};
	public:
		StorageOperation::Operations	m_operation;
		shared_ptr<HttpServer::Request> m_request;
		shared_ptr<HttpServer::Response> m_response;
};

class StoragePerformanceMonitor;
/**
 * The Storage API class - this class is responsible for the registration of all API
 * entry points in the storage API and the dispatch of those API calls to the internals
 * of the storage service and the storage plugin itself.
 */
class StorageApi {

public:
	StorageApi(const unsigned short port, const unsigned int threads, const unsigned int workerPoolSize);
	~StorageApi();
        static StorageApi *getInstance();
	void	initResources();
	void	setPlugin(StoragePlugin *);
	void	setReadingPlugin(StoragePlugin *);
	void	start();
	void	startServer();
	void	wait();
	void	stopServer();
	unsigned short getListenerPort();
	void	commonInsert(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request);
	void	commonSimpleQuery(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request);
	void	commonQuery(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request);
	void	commonUpdate(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request);
	void	commonDelete(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request);
	void	defaultResource(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request);
	void	readingAppend(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request);
	void	readingFetch(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request);
	void	readingQuery(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request);
	void	readingPurge(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request);
	void	readingRegister(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request);
	void	readingUnregister(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request);
	void	tableRegister(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request);
	void	tableUnregister(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request);
	void	createTableSnapshot(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request);
	void	loadTableSnapshot(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request);
	void	deleteTableSnapshot(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request);
	void	getTableSnapshots(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request);
	void	createStorageStream(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request);
	bool	readingStream(ReadingStream **readings, bool commit);
	void    createStorageSchema(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request);
	void 	storageTableInsert(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request);
	void    storageTableUpdate(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request);
	void    storageTableDelete(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request);
	void    storageTableSimpleQuery(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request);
	void    storageTableQuery(shared_ptr<HttpServer::Response> response, shared_ptr<HttpServer::Request> request);


	void	printList();
	bool	createSchema(const std::string& schema);
	void	setTimeout(long timeout)
		{
			if (m_server)
			{
				m_server->config.timeout_request = timeout;
			}
		};

	StoragePlugin	*getStoragePlugin() { return plugin; };
	StoragePerformanceMonitor
			*getPerformanceMonitor() { return m_perfMonitor; };
	void		worker();
	void		queue(StorageOperation::Operations op, shared_ptr<HttpServer::Request> request, shared_ptr<HttpServer::Response> response);
public:
	std::atomic<int>        m_workers_count;

private:
        static StorageApi       *m_instance;
        HttpServer              *m_server;
	unsigned short          m_port;
	unsigned int		m_threads;
        thread                  *m_thread;
	StoragePlugin		*plugin;
	StoragePlugin		*readingPlugin;
	StorageStats		stats;
	std::map<string, pair<int,std::list<std::string>::iterator>> m_seqnum_map;
	const unsigned int	max_entries_in_seqnum_map = 16;
	std::list<std::string>	seqnum_map_lru_list; // has the most recently accessed elements of m_seqnum_map at front of the dequeue
	std::mutex 		mtx_seqnum_map;
	StorageRegistry		registry;
	void			respond(shared_ptr<HttpServer::Response>, const string&);
	void			respond(shared_ptr<HttpServer::Response>, SimpleWeb::StatusCode, const string&);
	void			internalError(shared_ptr<HttpServer::Response>, const exception&);
	void			mapError(string&, PLUGIN_ERROR *);
	StreamHandler		*streamHandler;
	StoragePerformanceMonitor
				*m_perfMonitor;
	std::mutex		m_queueMutex;
	std::condition_variable	m_queueCV;
	std::queue<StorageOperation *>
				m_queue;
	std::vector<std::thread	*>
				m_workers;
	unsigned int		m_workerPoolSize;
	bool			m_shutdown;
};

/**
 * StoragePerformanceMonitor is a derived class from PerformanceMonitor
 * It allows direct writing of monitoring data to database
 */
class StoragePerformanceMonitor : public PerformanceMonitor {
	public:
		// Constructor with StorageApi pointer passed (also calling parent PerformanceMonitor constructor)
		StoragePerformanceMonitor(const std::string& name, StorageApi *api) :
					PerformanceMonitor(name, NULL), m_name(name), m_instance(api) {
		};
		// Direct write to storage of monitor data
		void writeData(const std::string& table, const InsertValues& values) {
			m_instance->getStoragePlugin()->commonInsert(table,
								values.toJSON());
		}
	private:
		std::string	m_name;
		StorageApi *m_instance;
};

#endif
