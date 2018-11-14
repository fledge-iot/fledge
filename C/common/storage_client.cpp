/*
 * FogLAMP storage service client
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <storage_client.h>
#include <reading.h>
#include <reading_set.h>
#include <rapidjson/document.h>
#include <rapidjson/error/en.h>
#include <service_record.h>
#include <string>
#include <sstream>
#include <iostream>
#include <thread>
#include <map>

using namespace std;
using namespace rapidjson;
using HttpClient = SimpleWeb::Client<SimpleWeb::HTTP>;

// handles m_client_map access
std::mutex sto_mtx_client_map;

/**
 * Storage Client constructor
 */
StorageClient::StorageClient(const string& hostname, const unsigned short port)
{

	m_logger = Logger::getLogger();
	m_urlbase << hostname << ":" << port;
}

/**
 * Storage Client constructor
 * stores the provided HttpClient into the map
 */
StorageClient::StorageClient(HttpClient *client) {

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
		m_logger->error("Failed to append reading: %s", ex.what());
	}
	return false;
}

/**
 * Append multiple readings
 */
bool StorageClient::readingAppend(const vector<Reading *>& readings)
{
	try {
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
		m_logger->error("Failed to append reading: %s", ex.what());
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
		m_logger->error("Failed to query readings: %s", ex.what());
		throw;
	} catch (exception* ex) {
		m_logger->error("Failed to query readings: %s", ex->what());
		delete ex;
		throw exception();
	}
	return 0;
}

/**
 * Retrieve a set of readings for sending on the northbound
 * interface of FogLAMP
 *
 * @param readingId	The ID of the reading which should be the first one to send
 * @param count		Maximum number if readings to return
 * @return ReadingSet	The set of readings
 */
ReadingSet *StorageClient::readingFetch(const unsigned long readingId, const unsigned long count)
{
	try {

		char url[256];
		snprintf(url, sizeof(url), "/storage/reading?id=%ld&count=%ld",
				readingId, count);

		auto res = this->getHttpClient()->request("GET", url);
		if (res->status_code.compare("200 OK") == 0)
		{
			ostringstream resultPayload;
			resultPayload << res->content.rdbuf();
			ReadingSet *result = new ReadingSet(resultPayload.str().c_str());
			return result;
		}
		ostringstream resultPayload;
		resultPayload << res->content.rdbuf();
		handleUnexpectedResponse("Fetch readings", res->status_code, resultPayload.str());
	} catch (exception& ex) {
		m_logger->error("Failed to fetch readings: %s", ex.what());
		throw;
	} catch (exception* ex) {
		m_logger->error("Failed to fetch readings: %s", ex->what());
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
		m_logger->error("Failed to purge readings: %s", ex.what());
		throw;
	} catch (exception* ex) {
		m_logger->error("Failed to purge readings: %s", ex->what());
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
		m_logger->error("Failed to fetch readings: %s", ex.what());
		throw;
	} catch (exception* ex) {
		m_logger->error("Failed to fetch readings: %s", ex->what());
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
			ResultSet *result = new ResultSet(resultPayload.str().c_str());
			return result;
		}
		handleUnexpectedResponse("Query table", res->status_code, resultPayload.str());
	} catch (exception& ex) {
		m_logger->error("Failed to query table %s: %s", tableName.c_str(), ex.what());
		throw;
	} catch (exception* ex) {
		m_logger->error("Failed to query table %s: %s", tableName.c_str(), ex->what());
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
		m_logger->error("Failed to query table %s: %s", tableName.c_str(), ex.what());
		throw;
	} catch (exception* ex) {
		m_logger->error("Failed to query table %s: %s", tableName.c_str(), ex->what());
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
	try {
		ostringstream convert;

		convert << values.toJSON();
		char url[128];
		snprintf(url, sizeof(url), "/storage/table/%s", tableName.c_str());
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
		m_logger->error("Failed to insert into table %s: %s", tableName.c_str(), ex.what());
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
 * @return int		The number of rows updated
 */
int StorageClient::updateTable(const string& tableName, const InsertValues& values, const Where& where)
{
	try {
		ostringstream convert;

		convert << "{ \"updates\" : [ ";
		convert << "{ \"where\" : ";
		convert << where.toJSON();
		convert << ", \"values\" : ";
		convert << values.toJSON();
		convert << " }";
		convert << " ] }";
		
		char url[128];
		snprintf(url, sizeof(url), "/storage/table/%s", tableName.c_str());
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
		handleUnexpectedResponse("Update table", res->status_code, resultPayload.str());
	} catch (exception& ex) {
		m_logger->error("Failed to update table %s: %s", tableName.c_str(), ex.what());
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
 * @return int		The number of rows updated
 */
int StorageClient::updateTable(const string& tableName, const ExpressionValues& values, const Where& where)
{
	try {
		ostringstream convert;

		convert << "{ \"updates\" : [ ";
		convert << "{ \"where\" : ";
		convert << where.toJSON();
		convert << ", \"expressions\" : ";
		convert << values.toJSON();
		convert << " }";
		convert << " ] }";
		
		char url[128];
		snprintf(url, sizeof(url), "/storage/table/%s", tableName.c_str());
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
		handleUnexpectedResponse("Update table", res->status_code, resultPayload.str());
	} catch (exception& ex) {
		m_logger->error("Failed to update table %s: %s", tableName.c_str(), ex.what());
		throw;
	}
	return -1;
}

/**
 * Update data into an arbitrary table
 *
 * @param tableName	The name of the table into which data will be added
 * @param updates	The expressions and condition pairs to update in the table
 * @return int		The number of rows updated
 */
int StorageClient::updateTable(const string& tableName, vector<pair<ExpressionValues *, Where *>>& updates)
{
	try {
		ostringstream convert;

		convert << "{ \"updates\" : [ ";
		for (vector<pair<ExpressionValues *, Where *>>::const_iterator it = updates.cbegin();
						 it != updates.cend(); ++it)
		{
			if (it != updates.cbegin())
			{
				convert << ", ";
			}
			convert << "{ \"where\" : ";
			convert << it->second->toJSON();
			convert << ", \"expressions\" : ";
			convert << it->first->toJSON();
			convert << " }";
		}
		convert << " ] }";
		
		char url[128];
		snprintf(url, sizeof(url), "/storage/table/%s", tableName.c_str());
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
		handleUnexpectedResponse("Update table", res->status_code, resultPayload.str());
	} catch (exception& ex) {
		m_logger->error("Failed to update table %s: %s", tableName.c_str(), ex.what());
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
 * @return int		The number of rows updated
 */
int StorageClient::updateTable(const string& tableName, const InsertValues& values, const ExpressionValues& expressions, const Where& where)
{
	try {
		ostringstream convert;

		convert << "{ \"updates\" : [ ";
		convert << "{ \"where\" : ";
		convert << where.toJSON();
		convert << ", \"values\" : ";
		convert << values.toJSON();
		convert << ", \"expressions\" : ";
		convert << expressions.toJSON();
		convert << " }";
		convert << " ] }";
		
		char url[128];
		snprintf(url, sizeof(url), "/storage/table/%s", tableName.c_str());
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
		handleUnexpectedResponse("Update table", res->status_code, resultPayload.str());
	} catch (exception& ex) {
		m_logger->error("Failed to update table %s: %s", tableName.c_str(), ex.what());
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
 * @return int		The number of rows updated
 */
int StorageClient::updateTable(const string& tableName, const JSONProperties& values, const Where& where)
{
	try {
		ostringstream convert;

		convert << "{ \"updates\" : [ ";
		convert << "{ \"where\" : ";
		convert << where.toJSON();
		convert << ", ";
		convert << values.toJSON();
		convert << " }";
		convert << " ] }";
		
		char url[128];
		snprintf(url, sizeof(url), "/storage/table/%s", tableName.c_str());
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
		handleUnexpectedResponse("Update table", res->status_code, resultPayload.str());
	} catch (exception& ex) {
		m_logger->error("Failed to update table %s: %s", tableName.c_str(), ex.what());
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
 * @return int		The number of rows updated
 */
int StorageClient::updateTable(const string& tableName, const InsertValues& values, const JSONProperties& jsonProp, const Where& where)
{
	try {
		ostringstream convert;

		convert << "{ \"updates\" : [ ";
		convert << "{ \"where\" : ";
		convert << where.toJSON();
		convert << ", \"values\" : ";
		convert << values.toJSON();
		convert << ", ";
		convert << jsonProp.toJSON();
		convert << " }";
		convert << " ] }";
		
		char url[128];
		snprintf(url, sizeof(url), "/storage/table/%s", tableName.c_str());
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
		handleUnexpectedResponse("Update table", res->status_code, resultPayload.str());
	} catch (exception& ex) {
		m_logger->error("Failed to update table %s: %s", tableName.c_str(), ex.what());
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
	try {
		ostringstream convert;

		convert << query.toJSON();
		char url[128];
		snprintf(url, sizeof(url), "/storage/table/%s", tableName.c_str());
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
		handleUnexpectedResponse("Delete from table", res->status_code, resultPayload.str());
	} catch (exception& ex) {
		m_logger->error("Failed to delete table data %s: %s", tableName.c_str(), ex.what());
		throw;
	}
	return -1;
}

/**
 * Standard logging method for all interactions
 *
 * @param operation	The operation beign undertaken
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
							  "/storage/reading/interest/" + assetName,
							  convert.str());
		if (res->status_code.compare("200 OK") == 0)
		{
			return true;
		}
		ostringstream resultPayload;
		resultPayload << res->content.rdbuf();
		handleUnexpectedResponse("Register asset",
					 res->status_code,
					 resultPayload.str());

		return false;
	} catch (exception& ex)
	{
		m_logger->error("Failed to register asset '%s': %s",
				assetName.c_str(),
				ex.what());
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
							  "/storage/reading/interest/" + assetName,
							  convert.str());
		if (res->status_code.compare("200 OK") == 0)
		{
			return true;
		}
		ostringstream resultPayload;
		resultPayload << res->content.rdbuf();
		handleUnexpectedResponse("Unregister asset",
					 res->status_code,
					 resultPayload.str());

		return false;
	} catch (exception& ex)
	{
		m_logger->error("Failed to unregister asset '%s': %s",
				assetName.c_str(),
				ex.what());
	}
	return false;
}
