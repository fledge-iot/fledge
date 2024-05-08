/*
 * Fledge storage service client
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch, Massimiliano Pinto
 */
#include <storage_client.h>
#include <reading.h>
#include <reading_set.h>
#include <reading_stream.h>
#include <rapidjson/document.h>
#include <rapidjson/error/en.h>
#include <management_client.h>
#include <service_record.h>
#include <string>
#include <sstream>
#include <iostream>
#include <thread>
#include <map>
#include <string_utils.h>
#include <sys/uio.h>
#include <errno.h>
#include <stdarg.h>

#define EXCEPTION_BUFFER_SIZE 120

#define INSTRUMENT		0
// Streaming is currently disabled due to an issue that causes the stream to
// hang after a period. Set the followign to 1 in order to enable streaming
#define ENABLE_STREAMING	0

#if INSTRUMENT
#include <sys/time.h>
#endif

using namespace std;
using namespace rapidjson;
using HttpClient = SimpleWeb::Client<SimpleWeb::HTTP>;

// handles m_client_map access
std::mutex sto_mtx_client_map;

/**
 * Storage Client constructor
 */
StorageClient::StorageClient(const string& hostname, const unsigned short port) : m_streaming(false), m_management(NULL)
{
	m_host = hostname;
	m_pid = getpid();
	m_logger = Logger::getLogger();
	m_urlbase << hostname << ":" << port;
}

/**
 * Storage Client constructor
 * stores the provided HttpClient into the map
 */
StorageClient::StorageClient(HttpClient *client) : m_streaming(false), m_management(NULL)
{

	std::thread::id thread_id = std::this_thread::get_id();

	sto_mtx_client_map.lock();
	m_client_map[thread_id] = client;
	sto_mtx_client_map.unlock();
}


/**
 * Destructor for storage client
 */
StorageClient::~StorageClient()
{
	std::map<std::thread::id, HttpClient *>::iterator item;

	// Deletes all the HttpClient objects created in the map
	for (item  = m_client_map.begin() ; item  != m_client_map.end() ; ++item)
	{
		delete item->second;
	}
}


/**
 * Delete HttpClient object for current thread
 */
bool StorageClient::deleteHttpClient()
{
	std::thread::id thread_id = std::this_thread::get_id();

	lock_guard<mutex> guard(sto_mtx_client_map);

	if(m_client_map.find(thread_id) == m_client_map.end())
		return false;

	ostringstream ss;
	ss << thread_id;
	Logger::getLogger()->debug("Storage client deleting HttpClient object @ %p for thread %s", m_client_map[thread_id], ss.str().c_str());
	
	delete m_client_map[thread_id];
	m_client_map.erase(thread_id);

	return true;
}


/**
 * Creates a HttpClient object for each thread
 * it stores/retrieves the reference to the HttpClient and the associated thread id in a map
 */
HttpClient *StorageClient::getHttpClient(void) {

	std::map<std::thread::id, HttpClient *>::iterator item;
	HttpClient *client;

	std::thread::id thread_id = std::this_thread::get_id();

	sto_mtx_client_map.lock();
	item = m_client_map.find(thread_id);

	if (item  == m_client_map.end() ) {

		// Adding a new HttpClient
		client = new HttpClient(m_urlbase.str());
		m_client_map[thread_id] = client;
		m_seqnum_map[thread_id].store(0);
		std::ostringstream ss;
		ss << std::this_thread::get_id();
	}
	else
	{
		client = item->second;
	}
	sto_mtx_client_map.unlock();

	return (client);
}

/**
 * Append a single reading
 */
bool StorageClient::readingAppend(Reading& reading)
{
	try {
		ostringstream convert;

		convert << "{ \"readings\" : [ ";
		convert << reading.toJSON();
		convert << " ] }";
		auto res = this->getHttpClient()->request("POST", "/storage/reading", convert.str());
		if (res->status_code.compare("200 OK") == 0)
		{
			return true;
		}
		ostringstream resultPayload;
		resultPayload << res->content.rdbuf();
		handleUnexpectedResponse("Append readings", res->status_code, resultPayload.str());
		return false;
	} catch (exception& ex) {
		handleException(ex, "append reading");
	}
	return false;
}

/**
 * Append multiple readings
 *
 * TODO implement a mechanism to force streamed or non-streamed mode
 */
bool StorageClient::readingAppend(const vector<Reading *>& readings)
{
#if INSTRUMENT
	struct timeval	start, t1, t2;
#endif
	if (m_streaming)
	{
		return streamReadings(readings);
	}
	// See if we should switch to stream mode
	struct timeval tmFirst, tmLast, dur;
	readings[0]->getUserTimestamp(&tmFirst);
	readings[readings.size()-1]->getUserTimestamp(&tmLast);
	timersub(&tmLast, &tmFirst, &dur);
	double timeSpan = dur.tv_sec + ((double)dur.tv_usec / 1000000);
	double rate = (double)readings.size() / timeSpan;
	// Stream functionality disabled
#if ENABLE_STREAMING
	if (rate > STREAM_THRESHOLD)
	{
		m_logger->info("Reading rate %.1f readings per second above threshold, attmempting to switch to stream mode", rate);
		if (openStream())
		{
			m_logger->info("Successfully switch to stream mode for readings");
			return streamReadings(readings);
		}
		m_logger->warn("Failed to switch to streaming mode");
	}
#endif
	static HttpClient *httpClient = this->getHttpClient(); // to initialize m_seqnum_map[thread_id] for this thread
	try {
		std::thread::id thread_id = std::this_thread::get_id();
		ostringstream ss;
		sto_mtx_client_map.lock();
		m_seqnum_map[thread_id].fetch_add(1);
		ss << m_pid << "#" << thread_id << "_" << m_seqnum_map[thread_id].load();
		sto_mtx_client_map.unlock();

		SimpleWeb::CaseInsensitiveMultimap headers = {{"SeqNum", ss.str()}};

#if INSTRUMENT
		gettimeofday(&start, NULL);
#endif
		ostringstream convert;
		convert << "{ \"readings\" : [ ";
		for (vector<Reading *>::const_iterator it = readings.cbegin();
						 it != readings.cend(); ++it)
		{
			if (it != readings.cbegin())
			{
				convert << ", ";
			}
			convert << (*it)->toJSON();
		}
		convert << " ] }";
#if INSTRUMENT
		gettimeofday(&t1, NULL);
#endif
		auto res = this->getHttpClient()->request("POST", "/storage/reading", convert.str(), headers);
#if INSTRUMENT
		gettimeofday(&t2, NULL);
#endif
		if (res->status_code.compare("200 OK") == 0)
		{
#if INSTRUMENT
			struct timeval tm;
			timersub(&t1, &start, &tm);
			double buildTime, requestTime;
			buildTime = tm.tv_sec + ((double)tm.tv_usec / 1000000);
			timersub(&t2, &t1, &tm);
			requestTime = tm.tv_sec + ((double)tm.tv_usec / 1000000);
			m_logger->info("Appended %d readings in %.3f seconds. Took %.3f seconds to build request", readings.size(), requestTime, buildTime);
			m_logger->info("%.1f Readings per second, request building %.2f%% of time", readings.size() / (buildTime + requestTime),
					(buildTime * 100) / (requestTime + buildTime));
			m_logger->info("Request block size %dK", strlen(convert.str().c_str())/1024);
#endif
			return true;
		}
		ostringstream resultPayload;
		resultPayload << res->content.rdbuf();
		handleUnexpectedResponse("Append readings", res->status_code, resultPayload.str());
		return false;
	} catch (exception& ex) {
		handleException(ex, "append readings");
	}
	return false;
}

/**
 * Perform a generic query against the readings data
 *
 * @param query		The query to execute
 * @return ResultSet	The result of the query
 */
ResultSet *StorageClient::readingQuery(const Query& query)
{
	try {
		ostringstream convert;

		convert << query.toJSON();
		auto res = this->getHttpClient()->request("PUT", "/storage/reading/query", convert.str());
		if (res->status_code.compare("200 OK") == 0)
		{
			ostringstream resultPayload;
			resultPayload << res->content.rdbuf();
			ResultSet *result = new ResultSet(resultPayload.str().c_str());
			return result;
		}
		ostringstream resultPayload;
		resultPayload << res->content.rdbuf();
		handleUnexpectedResponse("Query readings", res->status_code, resultPayload.str());
	} catch (exception& ex) {
		handleException(ex, "query readings");
		throw;
	} catch (exception* ex) {
		handleException(*ex, "query readings");
		delete ex;
		throw exception();
	}
	return 0;
}

/**
 * Perform a generic query against the readings data,
 * returning ReadingSet object
 *
 * @param query		The query to execute
 * @return ReadingSet	The result of the query
 */
ReadingSet *StorageClient::readingQueryToReadings(const Query& query)
{
	try {
		ostringstream convert;

		convert << query.toJSON();
		auto res = this->getHttpClient()->request("PUT", "/storage/reading/query", convert.str());
		if (res->status_code.compare("200 OK") == 0)
		{
			ostringstream resultPayload;
			resultPayload << res->content.rdbuf();
			ReadingSet* result = new ReadingSet(resultPayload.str().c_str());
			return result;
		}
		ostringstream resultPayload;
		resultPayload << res->content.rdbuf();
		handleUnexpectedResponse("Query readings", res->status_code, resultPayload.str());
	} catch (exception& ex) {
		handleException(ex, "query readings");
		throw;
	} catch (exception* ex) {
		handleException(*ex, "query readings");
		delete ex;
		throw exception();
	}
	return 0;
}

/**
 * Retrieve a set of readings for sending on the northbound
 * interface of Fledge
 *
 * @param readingId	The ID of the reading which should be the first one to send
 * @param count		Maximum number if readings to return
 * @return ReadingSet	The set of readings
 */
ReadingSet *StorageClient::readingFetch(const unsigned long readingId, const unsigned long count)
{
	try {

		char url[256];
		snprintf(url, sizeof(url), "/storage/reading?id=%lu&count=%lu",
				readingId, count);

		auto res = this->getHttpClient()->request("GET", url);
		if (res->status_code.compare("200 OK") == 0)
		{
			ostringstream resultPayload;
			resultPayload << res->content.rdbuf();
			ReadingSet *result = new ReadingSet(resultPayload.str());
			return result;
		}
		ostringstream resultPayload;
		resultPayload << res->content.rdbuf();
		handleUnexpectedResponse("Fetch readings", res->status_code, resultPayload.str());
	} catch (exception& ex) {
		handleException(ex, "fetch readings");
		throw;
	} catch (exception* ex) {
		handleException(*ex, "fetch readings");
		delete ex;
		throw exception();
	}
	return 0;
}

/**
 * Purge the readings by age
 *
 * @param age	Number of hours old a reading has to be to be considered for purging
 * @param sent	The ID of the last reading that was sent
 * @param purgeUnsent	Flag to control if unsent readings should be purged
 * @return PurgeResult	Data on the readings hat were purged
 */
PurgeResult StorageClient::readingPurgeByAge(unsigned long age, unsigned long sent, bool purgeUnsent)
{
	try {
		char url[256];
		snprintf(url, sizeof(url), "/storage/reading/purge?age=%ld&sent=%ld&flags=%s",
				age, sent, purgeUnsent ? "purge" : "retain");
		auto res = this->getHttpClient()->request("PUT", url);
		ostringstream resultPayload;
		resultPayload << res->content.rdbuf();
		if (res->status_code.compare("200 OK") == 0)
		{
			return PurgeResult(resultPayload.str());
		}
		handleUnexpectedResponse("Purge by age", res->status_code, resultPayload.str());
	} catch (exception& ex) {
		handleException(ex, "purge readings by age");
		throw;
	} catch (exception* ex) {
		handleException(*ex, "purge readings by age");
		delete ex;
		throw exception();
	}
	return PurgeResult();
}

/**
 * Purge the readings by size
 *
 * @param size		Desired maximum size of readings table
 * @param sent	The ID of the last reading that was sent
 * @param purgeUnsent	Flag to control if unsent readings should be purged
 * @return PurgeResult	Data on the readings hat were purged
 */
PurgeResult StorageClient::readingPurgeBySize(unsigned long size, unsigned long sent, bool purgeUnsent)
{
	try {
		char url[256];
		snprintf(url, sizeof(url), "/storage/reading/purge?size=%ld&sent=%ld&flags=%s",
				size, sent, purgeUnsent ? "purge" : "retain");
		auto res = this->getHttpClient()->request("PUT", url);
		if (res->status_code.compare("200 OK") == 0)
		{
			ostringstream resultPayload;
			resultPayload << res->content.rdbuf();
			return PurgeResult(resultPayload.str());
		}
	} catch (exception& ex) {
		handleException(ex, "purge readings by size");
		throw;
	} catch (exception* ex) {
		handleException(*ex, "purge readings by size");
		delete ex;
		throw exception();
	}
	return PurgeResult();
}

/**
 * Purge the readings by asset name
 *
 * @param asset		The name of the asset to purge
 * @return PurgeResult	Data on the readings that were purged
 */
PurgeResult StorageClient::readingPurgeByAsset(const string& asset)
{
	try {
		char url[256];
		snprintf(url, sizeof(url), "/storage/reading/purge?asset=%s", asset.c_str());
		auto res = this->getHttpClient()->request("PUT", url);
		if (res->status_code.compare("200 OK") == 0)
		{
			ostringstream resultPayload;
			resultPayload << res->content.rdbuf();
			return PurgeResult(resultPayload.str());
		}
	} catch (exception& ex) {
		handleException(ex, "purge readings by size");
		throw;
	} catch (exception* ex) {
		handleException(*ex, "purge readings by size");
		delete ex;
		throw exception();
	}
	return PurgeResult();
}

/**
 * Query a table
 *
 * @param tablename	The name of the table to query
 * @param query		The query payload
 * @return ResultSet*	The resultset of the query
 */
ResultSet *StorageClient::queryTable(const std::string& tableName, const Query& query)
{
	return queryTable(DEFAULT_SCHEMA, tableName, query);
}

/**
 * Query a table
 *
 * @param schema	The name of the schema to query
 * @param tablename	The name of the table to query
 * @param query		The query payload
 * @return ResultSet*	The resultset of the query
 */
ResultSet *StorageClient::queryTable(const std::string& schema, const std::string& tableName, const Query& query)
{
	try {
		ostringstream convert;

		convert << query.toJSON();
		char url[128];
		snprintf(url, sizeof(url), "/storage/schema/%s/table/%s/query", schema.c_str(), tableName.c_str());
		auto res = this->getHttpClient()->request("PUT", url, convert.str());
		ostringstream resultPayload;
		resultPayload << res->content.rdbuf();
		if (res->status_code.compare("200 OK") == 0)
		{
			ResultSet *result = new ResultSet(resultPayload.str().c_str());
			return result;
		}
		handleUnexpectedResponse("Query table", res->status_code, resultPayload.str());
	} catch (exception& ex) {
		handleException(ex, "query table %s", tableName.c_str());
		throw;
	} catch (exception* ex) {
		handleException(*ex, "query table %s", tableName.c_str());
		delete ex;
		throw exception();
	}
	return 0;
}

/**
 * Query a table and return a ReadingSet pointer
 *
 * @param tablename	The name of the table to query
 * @param query		The query payload
 * @return ReadingSet*	The resultset of the query as
 *			ReadingSet class pointer
 */
ReadingSet* StorageClient::queryTableToReadings(const std::string& tableName,
						const Query& query)
{
	try {
		ostringstream convert;

		convert << query.toJSON();
		char url[128];
		snprintf(url, sizeof(url), "/storage/table/%s/query", tableName.c_str());

		auto res = this->getHttpClient()->request("PUT", url, convert.str());
		ostringstream resultPayload;
		resultPayload << res->content.rdbuf();

		if (res->status_code.compare("200 OK") == 0)
		{
			ReadingSet* result = new ReadingSet(resultPayload.str().c_str());
			return result;
		}
		handleUnexpectedResponse("Query table", res->status_code, resultPayload.str());
	} catch (exception& ex) {
		handleException(ex, "query table %s to readings", tableName.c_str());
		throw;
	} catch (exception* ex) {
		handleException(*ex, "query table %s to readings", tableName.c_str());
		delete ex;
		throw exception();
	}
	return 0;
}

/**
 * Insert data into an arbitrary table
 *
 * @param tableName	The name of the table into which data will be added
 * @param values	The values to insert into the table
 * @return int		The number of rows inserted
 */
int StorageClient::insertTable(const string& tableName, const InsertValues& values)
{
	return insertTable(DEFAULT_SCHEMA, tableName, values);
}

/**
 * Insert data into an arbitrary table
 *
 * @param schema	The name of the schema to insert into
 * @param tableName	The name of the table into which data will be added
 * @param values	The values to insert into the table
 * @return int		The number of rows inserted
 */
int StorageClient::insertTable(const string& schema, const string& tableName, const InsertValues& values)
{
	try {
		ostringstream convert;

		convert << values.toJSON();
		char url[128];
		snprintf(url, sizeof(url), "/storage/schema/%s/table/%s", schema.c_str(), tableName.c_str());
		auto res = this->getHttpClient()->request("POST", url, convert.str());
		ostringstream resultPayload;
		resultPayload << res->content.rdbuf();
		if (res->status_code.compare("200 OK") == 0 || res->status_code.compare("201 Created") == 0)
		{
			Document doc;
			doc.Parse(resultPayload.str().c_str());
			if (doc.HasParseError())
			{
				m_logger->info("POST result %s.", res->status_code.c_str());
				m_logger->error("Failed to parse result of insertTable. %s. Document is %s",
						GetParseError_En(doc.GetParseError()),
						resultPayload.str().c_str());
				return -1;
			}
			else if (doc.HasMember("message"))
			{
				m_logger->error("Failed to append table data: %s",
					doc["message"].GetString());
				return -1;
			}
			return doc["rows_affected"].GetInt();
		}
		handleUnexpectedResponse("Insert table", res->status_code, resultPayload.str());
	} catch (exception& ex) {
		handleException(ex, "insert into table %s", tableName.c_str());
		throw;
	}
	return 0;
}

/**
 * Update data into an arbitrary table
 *
 * @param tableName	The name of the table into which data will be added
 * @param values	The values to insert into the table
 * @param where		The conditions to match the updated rows
 * @param modifier	Optional storage modifier
 * @return int		The number of rows updated
 */
int StorageClient::updateTable(const string& tableName, const InsertValues& values, const Where& where, const UpdateModifier *modifier)
{
	return updateTable(DEFAULT_SCHEMA, tableName, values, where, modifier);
}

/**
 * Update data into an arbitrary table
 *
 * @param schema	The name of the schema into which data will be added
 * @param tableName	The name of the table into which data will be added
 * @param values	The values to insert into the table
 * @param where		The conditions to match the updated rows
 * @param modifier	Optional storage modifier
 * @return int		The number of rows updated
 */
int StorageClient::updateTable(const string& schema, const string& tableName, const InsertValues& values, const Where& where, const UpdateModifier *modifier)
{
	static HttpClient *httpClient = this->getHttpClient(); // to initialize m_seqnum_map[thread_id] for this thread
	try {
		std::thread::id thread_id = std::this_thread::get_id();
		ostringstream ss;
		sto_mtx_client_map.lock();
		m_seqnum_map[thread_id].fetch_add(1);
		ss << m_pid << "#" << thread_id << "_" << m_seqnum_map[thread_id].load();
		sto_mtx_client_map.unlock();

		SimpleWeb::CaseInsensitiveMultimap headers = {{"SeqNum", ss.str()}};

		ostringstream convert;

		convert << "{ \"updates\" : [ {";
		if (modifier)
		{
			convert << "\"modifiers\" : [ \"" << modifier->toJSON() << "\" ], ";
		}
		convert << "\"where\" : ";
		convert << where.toJSON();
		convert << ", \"values\" : ";
		convert << values.toJSON();
		convert << " }";
		convert << " ] }";
		
		char url[128];
		snprintf(url, sizeof(url), "/storage/schema/%s/table/%s", schema.c_str(), tableName.c_str());
		auto res = this->getHttpClient()->request("PUT", url, convert.str(), headers);
		if (res->status_code.compare("200 OK") == 0)
		{
			ostringstream resultPayload;
			resultPayload << res->content.rdbuf();
			Document doc;
			doc.Parse(resultPayload.str().c_str());
			if (doc.HasParseError())
			{
				m_logger->info("PUT result %s.", res->status_code.c_str());
				m_logger->error("Failed to parse result of updateTable. %s",
						GetParseError_En(doc.GetParseError()));
				return -1;
			}
			else if (doc.HasMember("message"))
			{
				m_logger->error("Failed to update table data: %s",
					doc["message"].GetString());
				return -1;
			}
			return doc["rows_affected"].GetInt();
		}
		ostringstream resultPayload;
		resultPayload << res->content.rdbuf();
		handleUnexpectedResponse("Update table", tableName, res->status_code, resultPayload.str());
	} catch (exception& ex) {
		handleException(ex, "update table %s", tableName.c_str());
		throw;
	}
	return -1;
}

/**
 * Update data into an arbitrary table
 *
 * @param tableName	The name of the table into which data will be added
 * @param values	The expressions to update into the table
 * @param where		The conditions to match the updated rows
 * @param modifier	Optional update modifier
 * @return int		The number of rows updated
 */
int StorageClient::updateTable(const string& tableName, const ExpressionValues& values, const Where& where, const UpdateModifier *modifier)
{
	return updateTable(DEFAULT_SCHEMA, tableName, values, where, modifier);
}

/**
 * Update data into an arbitrary table
 *
 * @param schema	The name of the schema into which data will be added
 * @param tableName	The name of the table into which data will be added
 * @param values	The expressions to update into the table
 * @param where		The conditions to match the updated rows
 * @param modifier	Optional update modifier
 * @return int		The number of rows updated
 */
int StorageClient::updateTable(const string& schema, const string& tableName, const ExpressionValues& values, const Where& where, const UpdateModifier *modifier)
{
	static HttpClient *httpClient = this->getHttpClient(); // to initialize m_seqnum_map[thread_id] for this thread
	try {
		std::thread::id thread_id = std::this_thread::get_id();
		ostringstream ss;
		sto_mtx_client_map.lock();
		m_seqnum_map[thread_id].fetch_add(1);
		ss << m_pid << "#" << thread_id << "_" << m_seqnum_map[thread_id].load();
		sto_mtx_client_map.unlock();

		SimpleWeb::CaseInsensitiveMultimap headers = {{"SeqNum", ss.str()}};
		
		ostringstream convert;

		convert << "{ \"updates\" : [ {";
		if (modifier)
		{
			convert << "\"modifiers\" : [ \"" << modifier->toJSON() << "\" ], ";
		}
		convert << "\"where\" : ";
		convert << where.toJSON();
		convert << ", \"expressions\" : ";
		convert << values.toJSON();
		convert << " }";
		convert << " ] }";
		
		char url[128];
		snprintf(url, sizeof(url), "/storage/schema/%s/table/%s", schema.c_str(), tableName.c_str());
		auto res = this->getHttpClient()->request("PUT", url, convert.str(), headers);
		if (res->status_code.compare("200 OK") == 0)
		{
			ostringstream resultPayload;
			resultPayload << res->content.rdbuf();
			Document doc;
			doc.Parse(resultPayload.str().c_str());
			if (doc.HasParseError())
			{
				m_logger->info("PUT result %s.", res->status_code.c_str());
				m_logger->error("Failed to parse result of updateTable. %s",
						GetParseError_En(doc.GetParseError()));
				return -1;
			}
			else if (doc.HasMember("message"))
			{
				m_logger->error("Failed to update table data: %s",
					doc["message"].GetString());
				return -1;
			}
			return doc["rows_affected"].GetInt();
		}
		ostringstream resultPayload;
		resultPayload << res->content.rdbuf();
		handleUnexpectedResponse("Update table", tableName, res->status_code, resultPayload.str());
	} catch (exception& ex) {
		handleException(ex, "update table %s", tableName.c_str());
		throw;
	}
	return -1;
}

/**
 * Update data into an arbitrary table
 *
 * @param tableName	The name of the table into which data will be added
 * @param updates	The expressions and condition pairs to update in the table
 * @param modifier	Optional update modifier
 * @return int		The number of rows updated
 */
int StorageClient::updateTable(const string& tableName, vector<pair<ExpressionValues *, Where *>>& updates, const UpdateModifier *modifier)
{
	return updateTable(DEFAULT_SCHEMA, tableName, updates, modifier);
}

/**
 * Update data into an arbitrary table
 *
 * @param schema	The name of the schema into which data will be added
 * @param tableName	The name of the table into which data will be added
 * @param updates	The expressions and condition pairs to update in the table
 * @param modifier	Optional update modifier
 * @return int		The number of rows updated
 */
int StorageClient::updateTable(const string& schema, const string& tableName, vector<pair<ExpressionValues *, Where *>>& updates, const UpdateModifier *modifier)
{
	static HttpClient *httpClient = this->getHttpClient(); // to initialize m_seqnum_map[thread_id] for this thread
	try {
		std::thread::id thread_id = std::this_thread::get_id();
		ostringstream ss;
		sto_mtx_client_map.lock();
		m_seqnum_map[thread_id].fetch_add(1);
		ss << m_pid << "#" << thread_id << "_" << m_seqnum_map[thread_id].load();
		sto_mtx_client_map.unlock();

		SimpleWeb::CaseInsensitiveMultimap headers = {{"SeqNum", ss.str()}};
		
		ostringstream convert;
		convert << "{ \"updates\" : [ ";
		for (vector<pair<ExpressionValues *, Where *>>::const_iterator it = updates.cbegin();
						 it != updates.cend(); ++it)
		{
			if (it != updates.cbegin())
			{
				convert << ", ";
			}
			convert << "{ ";
			if (modifier)
			{
				convert << "\"modifiers\" : [ \"" << modifier->toJSON() << "\" ], ";
			}
			convert << "\"where\" : ";
			convert << it->second->toJSON();
			convert << ", \"expressions\" : ";
			convert << it->first->toJSON();
			convert << " }";
		}
		convert << " ] }";
		
		char url[128];
		snprintf(url, sizeof(url), "/storage/schema/%s/table/%s", schema.c_str(), tableName.c_str());
		auto res = this->getHttpClient()->request("PUT", url, convert.str(), headers);
		if (res->status_code.compare("200 OK") == 0)
		{
			ostringstream resultPayload;
			resultPayload << res->content.rdbuf();
			Document doc;
			doc.Parse(resultPayload.str().c_str());
			if (doc.HasParseError())
			{
				m_logger->info("PUT result %s.", res->status_code.c_str());
				m_logger->error("Failed to parse result of updateTable. %s",
						GetParseError_En(doc.GetParseError()));
				return -1;
			}
			else if (doc.HasMember("message"))
			{
				m_logger->error("Failed to update table data: %s",
					doc["message"].GetString());
				return -1;
			}
			return doc["rows_affected"].GetInt();
		}
		ostringstream resultPayload;
		resultPayload << res->content.rdbuf();
		handleUnexpectedResponse("Update table", tableName, res->status_code, resultPayload.str());
	} catch (exception& ex) {
		handleException(ex, "update table %s", tableName.c_str());
		throw;
	}
	return -1;
}


/**
 * Update data into an arbitrary table
 *
 * @param tableName	The name of the table into which data will be added
 * @param values	The values to insert into the table
 * @param expressions	The expression to update inthe table
 * @param where		The conditions to match the updated rows
 * @param modifier	Optional update modifier
 * @return int		The number of rows updated
 */
int StorageClient::updateTable(const string& tableName, const InsertValues& values, const ExpressionValues& expressions, const Where& where, const UpdateModifier *modifier)
{
	return updateTable(DEFAULT_SCHEMA, tableName, values, expressions, where, modifier);
}

/**
 * Update data into an arbitrary table
 *
 * @param schema	The name of the schema into which data will be added
 * @param tableName	The name of the table into which data will be added
 * @param values	The values to insert into the table
 * @param expressions	The expression to update inthe table
 * @param where		The conditions to match the updated rows
 * @param modifier	Optional update modifier
 * @return int		The number of rows updated
 */
int StorageClient::updateTable(const string& schema, const string& tableName, const InsertValues& values, const ExpressionValues& expressions, const Where& where, const UpdateModifier *modifier)
{
	try {
		ostringstream convert;

		convert << "{ \"updates\" : [ { ";
		if (modifier)
		{
			convert << "\"modifiers\" : [ \"" << modifier->toJSON() << "\" ], ";
		}
		convert << "\"where\" : ";
		convert << where.toJSON();
		convert << ", \"values\" : ";
		convert << values.toJSON();
		convert << ", \"expressions\" : ";
		convert << expressions.toJSON();
		convert << " }";
		convert << " ] }";
		
		char url[128];
		snprintf(url, sizeof(url), "/storage/schema/%s/table/%s", schema.c_str(), tableName.c_str());
		auto res = this->getHttpClient()->request("PUT", url, convert.str());
		if (res->status_code.compare("200 OK") == 0)
		{
			ostringstream resultPayload;
			resultPayload << res->content.rdbuf();
			Document doc;
			doc.Parse(resultPayload.str().c_str());
			if (doc.HasParseError())
			{
				m_logger->info("PUT result %s.", res->status_code.c_str());
				m_logger->error("Failed to parse result of updateTable. %s",
						GetParseError_En(doc.GetParseError()));
				return -1;
			}
			else if (doc.HasMember("message"))
			{
				m_logger->error("Failed to update table data: %s",
					doc["message"].GetString());
				return -1;
			}
			return doc["rows_affected"].GetInt();
		}
		ostringstream resultPayload;
		resultPayload << res->content.rdbuf();
		handleUnexpectedResponse("Update table", tableName, res->status_code, resultPayload.str());
	} catch (exception& ex) {
		handleException(ex, "update table %s", tableName.c_str());
		throw;
	}
	return -1;
}

/**
 * Update data into an arbitrary table
 *
 * @param tableName	The name of the table into which data will be added
 * @param json		The values to insert into the table
 * @param where		The conditions to match the updated rows
 * @param modifier	Optional update modifier
 * @return int		The number of rows updated
 */
int StorageClient::updateTable(const string& tableName, const JSONProperties& values, const Where& where, const UpdateModifier *modifier)
{
	return updateTable(DEFAULT_SCHEMA, tableName, values, where, modifier);
}

/**
 * Update data into an arbitrary table
 *
 * @param schema	The name of the schema into which data will be added
 * @param tableName	The name of the table into which data will be added
 * @param json		The values to insert into the table
 * @param where		The conditions to match the updated rows
 * @return int		The number of rows updated
 */
int StorageClient::updateTable(const string& schema, const string& tableName, const JSONProperties& values, const Where& where, const UpdateModifier *modifier)
{
	try {
		ostringstream convert;

		convert << "{ \"updates\" : [ {";
		if (modifier)
		{
			convert << "\"modifiers\" : [ \"" << modifier->toJSON() << "\" ]";
		}
		convert << "\"where\" : ";
		convert << where.toJSON();
		convert << ", ";
		convert << values.toJSON();
		convert << " }";
		convert << " ] }";
		
		char url[128];
		snprintf(url, sizeof(url), "/storage/schema/%s/table/%s", schema.c_str(), tableName.c_str());
		auto res = this->getHttpClient()->request("PUT", url, convert.str());
		if (res->status_code.compare("200 OK") == 0)
		{
			ostringstream resultPayload;
			resultPayload << res->content.rdbuf();
			Document doc;
			doc.Parse(resultPayload.str().c_str());
			if (doc.HasParseError())
			{
				m_logger->info("PUT result %s.", res->status_code.c_str());
				m_logger->error("Failed to parse result of updateTable. %s",
						GetParseError_En(doc.GetParseError()));
				return -1;
			}
			else if (doc.HasMember("message"))
			{
				m_logger->error("Failed to update table data: %s",
					doc["message"].GetString());
				return -1;
			}
			return doc["rows_affected"].GetInt();
		}
		ostringstream resultPayload;
		resultPayload << res->content.rdbuf();
		handleUnexpectedResponse("Update table", tableName, res->status_code, resultPayload.str());
	} catch (exception& ex) {
		handleException(ex, "update table %s", tableName.c_str());
		throw;
	}
	return -1;
}

/**
 * Update data into an arbitrary table
 *
 * @param tableName	The name of the table into which data will be added
 * @param values	The values to insert into the table
 * @param jsonProp	The JSON Properties to update
 * @param where		The conditions to match the updated rows
 * @param modifier	Optional update modifier
 * @return int		The number of rows updated
 */
int StorageClient::updateTable(const string& tableName, const InsertValues& values, const JSONProperties& jsonProp, const Where& where, const UpdateModifier *modifier)
{
	return updateTable(DEFAULT_SCHEMA, tableName, values, jsonProp, where, modifier);
}

/**
 * Update data into an arbitrary table
 *
 * @param schema	The name of the schema into which data will be added
 * @param tableName	The name of the table into which data will be added
 * @param values	The values to insert into the table
 * @param jsonProp	The JSON Properties to update
 * @param where		The conditions to match the updated rows
 * @param modifier	Optional update modifier
 * @return int		The number of rows updated
 */
int StorageClient::updateTable(const string& schema, const string& tableName, const InsertValues& values, const JSONProperties& jsonProp, const Where& where, const UpdateModifier *modifier)
{
	try {
		ostringstream convert;

		convert << "{ \"updates\" : [ {";
		if (modifier)
		{
			convert << "\"modifiers\" : [ \"" << modifier->toJSON() << "\", ";
		}
		convert << "\"where\" : ";
		convert << where.toJSON();
		convert << ", \"values\" : ";
		convert << values.toJSON();
		convert << ", ";
		convert << jsonProp.toJSON();
		convert << " }";
		convert << " ] }";
		
		char url[128];
		snprintf(url, sizeof(url), "/storage/schema/%s/table/%s", schema.c_str(), tableName.c_str());
		auto res = this->getHttpClient()->request("PUT", url, convert.str());
		if (res->status_code.compare("200 OK") == 0)
		{
			ostringstream resultPayload;
			resultPayload << res->content.rdbuf();
			Document doc;
			doc.Parse(resultPayload.str().c_str());
			if (doc.HasParseError())
			{
				m_logger->info("PUT result %s.", res->status_code.c_str());
				m_logger->error("Failed to parse result of updateTable. %s",
						GetParseError_En(doc.GetParseError()));
				return -1;
			}
			else if (doc.HasMember("message"))
			{
				m_logger->error("Failed to update table data: %s",
					doc["message"].GetString());
				return -1;
			}
			return doc["rows_affected"].GetInt();
		}
		ostringstream resultPayload;
		resultPayload << res->content.rdbuf();
		handleUnexpectedResponse("Update table", tableName, res->status_code, resultPayload.str());
	} catch (exception& ex) {
		handleException(ex, "update table %s", tableName.c_str());
		throw;
	}
	return -1;
}

/**
 * Delete from a table
 *
 * @param tablename	The name of the table to delete from
 * @param query		The query payload to match rows to delete
 * @return int	The number of rows deleted
 */
int StorageClient::deleteTable(const std::string& tableName, const Query& query)
{
	return deleteTable(DEFAULT_SCHEMA, tableName, query);
}

/**
 * Delete from a table
 *
 * @param schema	The name of the schema to delete from
 * @param tablename	The name of the table to delete from
 * @param query		The query payload to match rows to delete
 * @return int	The number of rows deleted
 */
int StorageClient::deleteTable(const std::string& schema, const std::string& tableName, const Query& query)
{
	try {
		ostringstream convert;

		convert << query.toJSON();
		char url[128];
		snprintf(url, sizeof(url), "/storage/schema/%s/table/%s", schema.c_str(), tableName.c_str());
		auto res = this->getHttpClient()->request("DELETE", url, convert.str());
		if (res->status_code.compare("200 OK") == 0)
		{
			ostringstream resultPayload;
			resultPayload << res->content.rdbuf();
			Document doc;
			doc.Parse(resultPayload.str().c_str());
			if (doc.HasParseError())
			{
				m_logger->info("PUT result %s.", res->status_code.c_str());
				m_logger->error("Failed to parse result of deleteTable. %s",
						GetParseError_En(doc.GetParseError()));
				return -1;
			}
			else if (doc.HasMember("message"))
			{
				m_logger->error("Failed to delete table data: %s",
					doc["message"].GetString());
				return -1;
			}
			return doc["rows_affected"].GetInt();
		}
		ostringstream resultPayload;
		resultPayload << res->content.rdbuf();
		handleUnexpectedResponse("Delete from table", tableName, res->status_code, resultPayload.str());
	} catch (exception& ex) {
		handleException(ex, "delete table date in %s", tableName.c_str());
		throw;
	}
	return -1;
}

/**
 * Standard logging method for all interactions
 *
 * @param operation	The operation being undertaken
 * @param table		The name of the table
 * @param responseCode	The HTTP response code
 * @param payload	The payload in the response message
 */
void StorageClient::handleUnexpectedResponse(const char *operation, const string& table,
			const string& responseCode,  const string& payload)
{
	string op(operation);
	op += " ";
	op += table;
	handleUnexpectedResponse(op.c_str(), responseCode, payload);
}

/**
 * Standard logging method for all interactions
 *
 * @param operation	The operation being undertaken
 * @param responseCode	The HTTP response code
 * @param payload	The payload in the response message
 */
void StorageClient::handleUnexpectedResponse(const char *operation,
			const string& responseCode,  const string& payload)
{
Document doc;

	doc.Parse(payload.c_str());
	if (!doc.HasParseError())
	{
		if (doc.HasMember("message"))
		{
			m_logger->info("%s completed with result %s", operation, 
							responseCode.c_str());
			m_logger->error("%s: %s", operation,
				doc["message"].GetString());
		}
	}
	else
	{
		m_logger->error("%s completed with result %s", operation, responseCode.c_str());
	}
}

/**
 * Register interest for a Reading asset name
 *
 * @param assetName	The asset name to register
 *			for readings data notification
 * @param callbackUrl	The callback URL to send readings data.
 * @return		True on success, false otherwise.
 */
bool StorageClient::registerAssetNotification(const string& assetName,
					      const string& callbackUrl)
{
	try
	{
		ostringstream convert;

		convert << "{ \"url\" : \"";
		convert << callbackUrl;
		convert << "\" }";
		auto res = this->getHttpClient()->request("POST",
							  "/storage/reading/interest/" + urlEncode(assetName),
							  convert.str());
		if (res->status_code.compare("200 OK") == 0)
		{
			return true;
		}
		ostringstream resultPayload;
		resultPayload << res->content.rdbuf();
		handleUnexpectedResponse("Register asset",
					 assetName,
					 res->status_code,
					 resultPayload.str());
		m_logger->error("/storage/reading/interest/%s: %s",
				urlEncode(assetName).c_str(), res->status_code.c_str());

		return false;
	} catch (exception& ex)
	{
		handleException(ex, "register asset '%s'", assetName.c_str());
	}
	return false;
}

/**
 * Unregister interest for a Reading asset name
 *
 * @param assetName	The asset name to unregister
 *			for readings data notification
 * @param callbackUrl	The callback URL provided in registration.
 * @return		True on success, false otherwise.
 */
bool StorageClient::unregisterAssetNotification(const string& assetName,
						const string& callbackUrl)
{
	try
	{
		ostringstream convert;

		convert << "{ \"url\" : \"";
		convert << callbackUrl;
		convert << "\" }";
		auto res = this->getHttpClient()->request("DELETE",
							  "/storage/reading/interest/" + urlEncode(assetName),
							  convert.str());
		if (res->status_code.compare("200 OK") == 0)
		{
			return true;
		}
		ostringstream resultPayload;
		resultPayload << res->content.rdbuf();
		handleUnexpectedResponse("Unregister asset",
					 assetName,
					 res->status_code,
					 resultPayload.str());

		return false;
	} catch (exception& ex)
	{
		handleException(ex, "unregister asset '%s'", assetName.c_str());
	}
	return false;
}

/**
 * Register interest for a table
 *
 * @param tableName	The table name to register for notification
 * @param tableKey	The key of interest in the table
 * @param tableKeyValues	The key values of interest
 * @param tableOperation	The table operation of interest (insert/update/delete)
 * @param callbackUrl	The callback URL to send change data
 * @return		True on success, false otherwise.
 */
bool StorageClient::registerTableNotification(const string& tableName, const string& key, std::vector<std::string> keyValues,
					      const string& operation, const string& callbackUrl)
{
	try
	{
		ostringstream keyValuesStr;
		for (auto & s : keyValues)
		{
			keyValuesStr << "\"" << s << "\"";
			if (&s != &keyValues.back())
				keyValuesStr << ", ";
		}
		
		ostringstream convert;

		convert << "{ ";
		convert << "\"url\" : \"" << callbackUrl << "\", ";
		convert << "\"key\" : \"" << key << "\", ";
		convert << "\"values\" : [" << keyValuesStr.str() << "], ";
		convert << "\"operation\" : \"" << operation << "\" ";
		convert << "}";
		
		auto res = this->getHttpClient()->request("POST",
							  "/storage/table/interest/" + urlEncode(tableName),
							  convert.str());
		if (res->status_code.compare("200 OK") == 0)
		{
			return true;
		}
		ostringstream resultPayload;
		resultPayload << res->content.rdbuf();
		handleUnexpectedResponse("Register table",
					 tableName,
					 res->status_code,
					 resultPayload.str());
		m_logger->error("POST /storage/table/interest/%s: %s",
				urlEncode(tableName).c_str(), res->status_code.c_str());

		return false;
	} catch (exception& ex)
	{
		handleException(ex, "register table '%s'", tableName.c_str());
	}
	return false;
}

/**
 * Unregister interest for a table name
 *
 * @param tableName	The table name to unregister interest in
 * @param tableKey	The key of interest in the table
 * @param tableKeyValues	The key values of interest
 * @param tableOperation	The table operation of interest (insert/update/delete)
 * @param callbackUrl	The callback URL to send change data
 * @return		True on success, false otherwise.
 */
bool StorageClient::unregisterTableNotification(const string& tableName, const string& key, std::vector<std::string> keyValues,
					      const string& operation, const string& callbackUrl)
{
	try
	{
		ostringstream keyValuesStr;
		for (auto & s : keyValues)
		{
			keyValuesStr << "\"" << s << "\"";
			if (&s != &keyValues.back())
				keyValuesStr << ", ";
		}
		
		ostringstream convert;

		convert << "{ ";
		convert << "\"url\" : \"" << callbackUrl << "\", ";
		convert << "\"key\" : \"" << key << "\", ";
		convert << "\"values\" : [" << keyValuesStr.str() << "], ";
		convert << "\"operation\" : \"" << operation << "\" ";
		convert << "}";
		
		auto res = this->getHttpClient()->request("DELETE",
							  "/storage/table/interest/" + urlEncode(tableName),
							  convert.str());
		if (res->status_code.compare("200 OK") == 0)
		{
			return true;
		}
		ostringstream resultPayload;
		resultPayload << res->content.rdbuf();
		handleUnexpectedResponse("Unregister table",
					 tableName,
					 res->status_code,
					 resultPayload.str());
		m_logger->error("DELETE /storage/table/interest/%s: %s",
				urlEncode(tableName).c_str(), res->status_code.c_str());

		return false;
	} catch (exception& ex)
	{
		handleException(ex, "unregister table '%s'", tableName.c_str());
	}
	return false;
}

/*
 * Attempt to open a streaming connection to the storage service. We use a REST API
 * call to create the stream. If successful this call will return a port and a token
 * to use when sending data via the stream.
 *
 * @return bool		Return true if the stream was setup
 */
bool StorageClient::openStream()
{
	try {
		auto res = this->getHttpClient()->request("POST", "/storage/reading/stream");
		m_logger->info("POST /storage/reading/stream returned: %s", res->status_code.c_str());
		if (res->status_code.compare("200 OK") == 0)
		{
			ostringstream resultPayload;
			resultPayload << res->content.rdbuf();
			Document doc;
			doc.Parse(resultPayload.str().c_str());
			if (doc.HasParseError())
			{
				m_logger->info("POST result %s.", res->status_code.c_str());
				m_logger->error("Failed to parse result of createStream. %s. Document is %s",
						GetParseError_En(doc.GetParseError()),
						resultPayload.str().c_str());
				return false;
			}
			else if (doc.HasMember("message"))
			{
				m_logger->error("Failed to switch to stream mode: %s",
					doc["message"].GetString());
				return false;
			}
			int port, token;
			if ((!doc.HasMember("port")) || (!doc.HasMember("token")))
			{
				m_logger->error("Missing items in stream creation response");
				return false;
			}
		       	port = doc["port"].GetInt();
			token = doc["token"].GetInt();
			if ((m_stream = socket(AF_INET, SOCK_STREAM, 0)) == -1)
        		{
				m_logger->error("Unable to create socket");
				return false;
			}
			struct sockaddr_in serv_addr;
			hostent *server;
			if ((server = gethostbyname(m_host.c_str())) == NULL)
			{
				m_logger->error("Unable to resolve hostname for reading stream: %s", m_host.c_str());
				return false;
			}
			bzero((char *) &serv_addr, sizeof(serv_addr));
			serv_addr.sin_family = AF_INET;
			bcopy((char *)server->h_addr, (char *)&serv_addr.sin_addr.s_addr, server->h_length);
			serv_addr.sin_port = htons(port);
			if (connect(m_stream, (struct sockaddr *) &serv_addr, sizeof(serv_addr)) < 0)
			{
				Logger::getLogger()->warn("Unable to connect to storage streaming server: %s, %d", m_host.c_str(), port);
				return false;
			}
			RDSConnectHeader conhdr;
			conhdr.magic = RDS_CONNECTION_MAGIC;
			conhdr.token = token;
			if (write(m_stream, &conhdr, sizeof(conhdr)) != sizeof(conhdr))
			{
				Logger::getLogger()->warn("Failed to write connection header: %s", strerror(errno));
				return false;
			}
			m_streaming = true;
			m_logger->info("Storage stream succesfully created");
			return true;
		}
		ostringstream resultPayload;
		resultPayload << res->content.rdbuf();
		handleUnexpectedResponse("Create reading stream", res->status_code, resultPayload.str());
		return false;
	} catch (exception& ex) {
		handleException(ex, "create reading stream");
	}
	m_logger->error("Fallen through!");
	return false;
}

/**
 * Stream a set of readings to the storage service.
 *
 * The stream uses a TCP connection to the storage system, it sends
 * blocks of readings to the storage engine and bypasses the usual 
 * JSON conversion and imoprtantly parsing on the storage system
 * side.
 *
 * A block of readings is introduced by a block header, the block
 * header contains a magic number, the block number and the count
 * of the number of readings in a block.
 *
 * Each reading within the block is preceeded by a reading header
 * that contains a magic number, a reading number within the block,
 * The length of the asset name for the reading, the length of the
 * payload within the reading. The reading itself follows the herader
 * and consists of the timestamp as a binary timeval structure, the name
 * of the asset, including the null terminator. If the asset name length
 * is 0 then no asset name is sent and the name of the asset is the same
 * as the previous asset in the block. Following this the paylod is included.
 *
 * Each block is sent to the storage layer in a number of chunks rather
 * that a single write per block. The implementation make use of the
 * Linux scatter/gather IO calls to reduce the number of copies of data
 * that are required.
 *
 * Currently there is no acknowledement handling as TCP is used as the underlying
 * transport and the TCP acknowledgement is assumed to be a good enough 
 * indication of delivery.
 *
 * TODO Deal with acknowledgements, add error checking/recovery
 *
 * @param readings	The readings to stream
 * @return bool		True if the readings have been sent
 */
bool StorageClient::streamReadings(const std::vector<Reading *> & readings)
{
RDSBlockHeader   		blkhdr;
RDSReadingHeader 		rdhdrs[STREAM_BLK_SIZE];
register RDSReadingHeader	*phdr;
struct iovec			iovs[STREAM_BLK_SIZE * 4], *iovp;
string				payloads[STREAM_BLK_SIZE];
struct timeval			tm[STREAM_BLK_SIZE];
ssize_t				n, length = 0;
string				lastAsset;


	if (!m_streaming)
	{
		m_logger->warn("Attempt to send data via a storage stream when streaming is not setup");
		return false;
	}

	/*
	 * Assemble and write the block header. This header contains information
	 * to synchronise the blocks of data and also the number of readings
	 * to expect within the block.
	 */
	blkhdr.magic = RDS_BLOCK_MAGIC;
	blkhdr.blockNumber = m_readingBlock++;
	blkhdr.count = readings.size();
	if ((n = write(m_stream, &blkhdr, sizeof(blkhdr))) != sizeof(blkhdr))
	{
		if (errno == EPIPE || errno == ECONNRESET)
		{
			Logger::getLogger()->error("Storage service has closed stream unexpectedly");
			m_streaming = false;
		}
		else
		{
			Logger::getLogger()->error("Failed to write block header: %s", strerror(errno));
		}
		return false;
	}

	/*
	 * Use the writev scatter/gather interface to send the reading headers and reading data.
	 * We sent chunks of data in order to allow the parallel sending and unpacking process
	 * at the two ends. The chunk size is STREAM_BLK_SIZE readings.
	 */
	iovp = iovs;
	phdr = rdhdrs;
	int offset = 0;
	for (int i = 0; i < readings.size(); i++)
	{
		phdr->magic = RDS_READING_MAGIC;
		phdr->readingNo = i;
		string assetCode = readings[i]->getAssetName();
		if (i > 0 && assetCode.compare(lastAsset) == 0)
		{
			// Asset name is unchanged so don't send it
			phdr->assetLength = 0;
		}
		else
		{
			// Asset name has changed or this is the first asset in the block
			lastAsset = assetCode;
			phdr->assetLength = assetCode.length() + 1;
		}

		// Always generate the JSON variant of the data points and send
		payloads[offset] = readings[i]->getDatapointsJSON();
		phdr->payloadLength = payloads[offset].length() + 1;

		// Add the reading header
		iovp->iov_base = phdr;
		iovp->iov_len = sizeof(RDSReadingHeader);
		length += iovp->iov_len;
		iovp++;

		// Reading user timestamp
		readings[i]->getUserTimestamp(&tm[offset]);
		iovp->iov_base = &tm[offset];
		iovp->iov_len = sizeof(struct timeval);
		length += iovp->iov_len;
		iovp++;

		// If the asset code has changed than add that
		if (phdr->assetLength)
		{
			iovp->iov_base = (void *)(readings[i]->getAssetName().c_str());	// Cast away const due to iovec definition
			iovp->iov_len = phdr->assetLength;
			length += iovp->iov_len;
			iovp++;
		}

		// Add the data points themselves
		iovp->iov_base = (void *)(payloads[offset].c_str()); // Cast away const due to iovec definition
		iovp->iov_len = phdr->payloadLength;
		length += iovp->iov_len;
		iovp++;

		offset++;
		if (offset == STREAM_BLK_SIZE - 1)
		{
			if (iovp - iovs > STREAM_BLK_SIZE * 4)
				Logger::getLogger()->error("Too many iov blocks %d", iovp - iovs);
			// Send a chunk of readings in the block
			n = writev(m_stream, (const iovec *)iovs, iovp - iovs);
			if (n == -1)
			{
				if (errno == EPIPE || errno == ECONNRESET)
				{
					Logger::getLogger()->error("Stream has been closed by the storage service");
					m_streaming = false;
				}
				Logger::getLogger()->error("Write of block %d filed: %s",
							m_readingBlock - 1, strerror(errno));
				return false;
			}
			else if (n < length)
			{
				Logger::getLogger()->error("Write of block short, %d < %d: %s",
							n, length, strerror(errno));
				return false;
			}
			else if (n > length)
			{
				Logger::getLogger()->fatal("Long write %d < %d", length, n);
			}
			offset = 0;
			length = 0;
			iovp = iovs;
			phdr = rdhdrs;
		}
		else
		{
			phdr++;
		}
	}

	if (length)	// Remaining data to be sent to finish the block
	{
		n = writev(m_stream, (const iovec *)iovs, iovp - iovs);
		if (n == -1)
		{
			if (errno == EPIPE || errno == ECONNRESET)
			{
				Logger::getLogger()->error("Stream has been closed by the storage service");
				m_streaming = false;
			}
			Logger::getLogger()->error("Write of block %d filed: %s",
						m_readingBlock - 1, strerror(errno));
			return false;
		}
		else if (n < length)
		{
			Logger::getLogger()->error("Write of block short, %d < %d: %s",
						n, length, strerror(errno));
			return false;
		}
		else if (n > length)
		{
			Logger::getLogger()->fatal("Long write %d < %d", length, n);
		}
	}
	Logger::getLogger()->info("Written block of %d readings via streaming connection", readings.size());
	return true;
}

/**
 * Handle exceptions encountered when communicating to the storage system
 *
 * @param ex	The exception we are handling
 */
void StorageClient::handleException(const exception& ex, const char *operation, ...)
{
	char buf[EXCEPTION_BUFFER_SIZE];
	va_list ap;
	va_start(ap, operation);
	vsnprintf(buf, sizeof(buf), operation, ap);
	va_end(ap);
	// Firstly deal with not flooding the log with repeated exceptions
	const char *what = ex.what();
	if (m_lastException.empty())	// First exception
	{
		m_lastException = what;
		m_exRepeat = 0;
		m_backoff = SC_INITIAL_BACKOFF;
		m_logger->error("Failed to %s: %s", buf, m_lastException.c_str());
	}
	else if (m_lastException.compare(what) == 0)
	{
		m_exRepeat++;
		if ((m_exRepeat % m_backoff) == 0)
		{
			if (m_backoff < SC_MAX_BACKOFF)
				m_backoff *= 2;
			m_logger->error("Storage client repeated failure: %s", m_lastException.c_str());
		}
	}
	else
	{
		m_logger->error("Storage client failure: %s repeated %d times", m_lastException.c_str(), m_exRepeat);
		m_backoff = SC_INITIAL_BACKOFF;
		m_lastException = what;
		m_logger->error("Failed to %s: %s", buf, m_lastException.c_str());
	}

	// Now implement some recovery strategies
	if (m_lastException.compare("Connection refused") == 0)
	{
		// This is probably because the storage service has gone down
		if (m_management)
		{
			// Get a handle on the storage layer
			ServiceRecord storageRecord("Fledge Storage");
			if (!m_management->getService(storageRecord))
			{
				m_logger->fatal("Unable to find a storage service from service registry, exiting...");
				exit(1);
			}
			m_urlbase << storageRecord.getAddress() << ":" << storageRecord.getPort();
		}
		if (m_exRepeat >= SC_INITIAL_BACKOFF * 2)
		{
			// We clearly tried to recover a number of times without success, simply exit at this stage
			m_logger->fatal("Storage service appears to have failed and unable to connect to core, exiting...");
			exit(1);
		}
	}
}

/**
 * Function to create Storage Schema
 */
bool StorageClient::createSchema(const std::string& payload)
{
        try {
                auto res = this->getHttpClient()->request("POST", "/storage/schema", payload.c_str());
                if (res->status_code.compare("200 OK") == 0)
                {
                        return true;
                }
                ostringstream resultPayload;
                resultPayload << res->content.rdbuf();
                handleUnexpectedResponse("Post Storage Schema", res->status_code, resultPayload.str());
                return false;
        } catch (exception& ex) {
                handleException(ex, "post storage schema");
        }
        return false;
}

/**
 * Update data into an arbitrary table
 *
 * @param schema        The name of the schema into which data will be added
 * @param tableName     The name of the table into which data will be added
 * @param updates       The values and condition pairs to update in the table
 * @param modifier      Optional update modifier
 * @return int          The number of rows updated
 */
int StorageClient::updateTable(const string& schema, const string& tableName, std::vector<std::pair<InsertValue*, Where*> >& updates, const UpdateModifier *modifier)
{
        static HttpClient *httpClient = this->getHttpClient(); // to initialize m_seqnum_map[thread_id] for this thread
        try {
                std::thread::id thread_id = std::this_thread::get_id();
                ostringstream ss;
                sto_mtx_client_map.lock();
                m_seqnum_map[thread_id].fetch_add(1);
                ss << m_pid << "#" << thread_id << "_" << m_seqnum_map[thread_id].load();
                sto_mtx_client_map.unlock();

                SimpleWeb::CaseInsensitiveMultimap headers = {{"SeqNum", ss.str()}};

                ostringstream convert;
                convert << "{ \"updates\" : [ ";

		for (vector<pair<InsertValue *, Where *>>::const_iterator it = updates.cbegin();
                                                 it != updates.cend(); ++it)
                {
                        if (it != updates.cbegin())
                        {
                                convert << ", ";
                        }
                        convert << "{ ";
                        if (modifier)
                        {
                                convert << "\"modifiers\" : [ \"" << modifier->toJSON() << "\" ], ";
                        }
                        convert << "\"where\" : ";
                        convert << it->second->toJSON();
                        convert << ", \"values\" : ";
                        convert << " { " << it->first->toJSON() << " } ";
                        convert << " }";
                }
                convert << " ] }";

                char url[128];
                snprintf(url, sizeof(url), "/storage/schema/%s/table/%s", schema.c_str(), tableName.c_str());
                auto res = this->getHttpClient()->request("PUT", url, convert.str(), headers);

		if (res->status_code.compare("200 OK") == 0)
                {
                        ostringstream resultPayload;
                        resultPayload << res->content.rdbuf();
                        Document doc;
                        doc.Parse(resultPayload.str().c_str());
                        if (doc.HasParseError())
                        {
                                m_logger->info("PUT result %s.", res->status_code.c_str());
                                m_logger->error("Failed to parse result of updateTable. %s",
                                                GetParseError_En(doc.GetParseError()));
                                return -1;
                        }
                        else if (doc.HasMember("message"))
                        {
                                m_logger->error("Failed to update table data: %s",
                                        doc["message"].GetString());
                                return -1;
                        }
                        return doc["rows_affected"].GetInt();
                }
                ostringstream resultPayload;
                resultPayload << res->content.rdbuf();
                handleUnexpectedResponse("Update table", tableName, res->status_code, resultPayload.str());
        } catch (exception& ex) {
                handleException(ex, "update table %s", tableName.c_str());
                throw;
        }
        return -1;
}

/**
 * Update data into an arbitrary table
 *
 * @param tableName     The name of the table into which data will be added
 * @param updates       The values to insert into the table
 * @param modifier      Optional storage modifier
 * @return int          The number of rows updated
 */

int StorageClient::updateTable(const string& tableName, std::vector<std::pair<InsertValue*, Where*> >& updates, const UpdateModifier *modifier)
{
	return updateTable(DEFAULT_SCHEMA, tableName, updates, modifier);
}

/**
 * Insert data into an arbitrary table
 *
 * @param tableName     The name of the table into which data will be added
 * @param values        The values to insert into the table
 * @return int          The number of rows inserted
 */
int StorageClient::insertTable(const string& tableName, const std::vector<InsertValues>&  values)
{
	return insertTable(DEFAULT_SCHEMA, tableName, values);
}
/**
 * Insert data into an arbitrary table
 *
 * @param schema        The name of the schema to insert into
 * @param tableName     The name of the table into which data will be added
 * @param values        The values to insert into the table
 * @return int          The number of rows inserted
 */
int StorageClient::insertTable(const string& schema, const string& tableName, const std::vector<InsertValues>&  values)
{
        try {
		ostringstream convert;
		convert << "{ \"inserts\": [" ;
                for (std::vector<InsertValues>::const_iterator it = values.cbegin();
                                                 it != values.cend(); ++it)
                {
                        if (it != values.cbegin())
                        {
                                convert << ", ";
                        }
                        convert <<  it->toJSON() ;
                }
		convert << "]}";

                char url[1000];
                snprintf(url, sizeof(url), "/storage/schema/%s/table/%s", schema.c_str(), tableName.c_str());

                auto res = this->getHttpClient()->request("POST", url, convert.str());
                ostringstream resultPayload;
                resultPayload << res->content.rdbuf();
                if (res->status_code.compare("200 OK") == 0 || res->status_code.compare("201 Created") == 0)
                {

                        Document doc;
                        doc.Parse(resultPayload.str().c_str());
                        if (doc.HasParseError())
                        {
                                m_logger->info("POST result %s.", res->status_code.c_str());
                                m_logger->error("Failed to parse result of insertTable. %s. Document is %s",
                                                GetParseError_En(doc.GetParseError()),
                                                resultPayload.str().c_str());
                                return -1;
                        }
                        else if (doc.HasMember("rows_affected"))
			{
	                       return doc["rows_affected"].GetInt();
			}
                }
                handleUnexpectedResponse("Insert table", res->status_code, resultPayload.str());
        } catch (exception& ex) {
                handleException(ex, "insert into table %s", tableName.c_str());
                throw;
        }
        return 0;
}
