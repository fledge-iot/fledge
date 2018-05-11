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

using namespace std;
using namespace rapidjson;
using HttpClient = SimpleWeb::Client<SimpleWeb::HTTP>;


/**
 * Storage Client constructor
 */
StorageClient::StorageClient(const string& hostname, const unsigned short port)
{
ostringstream urlbase;

	m_logger = Logger::getLogger();
	urlbase << hostname << ":" << port;
	m_client = new HttpClient(urlbase.str());
}

/**
 * Destructor for storage client
 */
StorageClient::~StorageClient()
{
	delete m_client;
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
		auto res = m_client->request("POST", "/storage/reading", convert.str());
		if (res->status_code.compare("200 OK") == 0)
		{
			return true;
		}
		Document doc;
		doc.Parse(res->content.string().c_str());
		if (doc.HasParseError())
		{
			m_logger->info("POST readings result %s.", res->status_code.c_str());
			m_logger->error("Failed to parse result of readingAppend. %s",
					GetParseError_En(doc.GetParseError()));
		}
		else if (doc.HasMember("message"))
		{
			m_logger->error("Failed to append readings: %s",
				doc["message"].GetString());
		}
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
		auto res = m_client->request("POST", "/storage/reading", convert.str());
		if (res->status_code.compare("200 OK") == 0)
		{
			return true;
		}
		ostringstream resultPayload;
		resultPayload << res->content.rdbuf();
		Document doc;
		doc.Parse(resultPayload.str().c_str());
		if (doc.HasParseError())
		{
			m_logger->info("POST readings result %s.", res->status_code.c_str());
			m_logger->error("Failed to parse result of readingAppend. %s",
					GetParseError_En(doc.GetParseError()));
			m_logger->error("Unparsable response payload is: %s.", resultPayload.str().c_str());
		}
		else if (doc.HasMember("message"))
		{
			m_logger->info("POST readings result %s", res->status_code.c_str());
			m_logger->error("Failed to append readings: %s",
				doc["message"].GetString());
		}
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
		auto res = m_client->request("PUT", "/storage/reading/query", convert.str());
		if (res->status_code.compare("200 OK") == 0)
		{
			ostringstream resultPayload;
			resultPayload << res->content.rdbuf();
			ResultSet *result = new ResultSet(resultPayload.str().c_str());
			return result;
		}
	} catch (exception& ex) {
		m_logger->error("Failed to query readings: %s", ex.what());
		throw;
	}
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
		auto res = m_client->request("GET", url);
		if (res->status_code.compare("200 OK") == 0)
		{
			ostringstream resultPayload;
			resultPayload << res->content.rdbuf();
			ReadingSet *result = new ReadingSet(resultPayload.str().c_str());
			return result;
		}
	} catch (exception& ex) {
		m_logger->error("Failed to fetch readings: %s", ex.what());
		throw;
	}
}

/**
 * Purge the readings by age
 *
 * @param age	Number of hours old a reading has to be to be considered for purging
 * @param sent	The ID of the last readign that was sent
 * @param purgeUnsent	Flag to control if unsent readings should be purged
 * @return PurgeResult	Data on the readings hat were purged
 */
PurgeResult StorageClient::readingPurgeByAge(unsigned long age, unsigned long sent, bool purgeUnsent)
{
	try {
		char url[256];
		snprintf(url, sizeof(url), "/storage/reading/purge?age=%ld&sent=%ld&flags=%s",
				age, sent, purgeUnsent ? "purge" : "retain");
		auto res = m_client->request("PUT", url);
		if (res->status_code.compare("200 OK") == 0)
		{
			ostringstream resultPayload;
			resultPayload << res->content.rdbuf();
			return PurgeResult(resultPayload.str());
		}
	} catch (exception& ex) {
		m_logger->error("Failed to fetch readings: %s", ex.what());
		throw;
	}
}

/**
 * Purge the readings by size
 *
 * @param size		Desired maximum size of readings table
 * @param sent	The ID of the last readign that was sent
 * @param purgeUnsent	Flag to control if unsent readings should be purged
 * @return PurgeResult	Data on the readings hat were purged
 */
PurgeResult StorageClient::readingPurgeBySize(unsigned long size, unsigned long sent, bool purgeUnsent)
{
	try {
		char url[256];
		snprintf(url, sizeof(url), "/storage/reading/purge?size=%ld&sent=%ld&flags=%s",
				size, sent, purgeUnsent ? "purge" : "retain");
		auto res = m_client->request("PUT", url);
		if (res->status_code.compare("200 OK") == 0)
		{
			ostringstream resultPayload;
			resultPayload << res->content.rdbuf();
			return PurgeResult(resultPayload.str());
		}
	} catch (exception& ex) {
		m_logger->error("Failed to fetch readings: %s", ex.what());
		throw;
	}
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
		auto res = m_client->request("PUT", url, convert.str());
		if (res->status_code.compare("200 OK") == 0)
		{
			ostringstream resultPayload;
			resultPayload << res->content.rdbuf();
			ResultSet *result = new ResultSet(resultPayload.str().c_str());
			return result;
		}
	} catch (exception& ex) {
		m_logger->error("Failed to query table %s: %s", tableName.c_str(), ex.what());
		throw;
	}
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
		auto res = m_client->request("POST", url, convert.str());
		if (res->status_code.compare("200 OK") == 0 || res->status_code.compare("201 Created") == 0)
		{
			ostringstream resultPayload;
			resultPayload << res->content.rdbuf();
			Document doc;
			doc.Parse(res->content.string().c_str());
			if (doc.HasParseError())
			{
				m_logger->info("POST result %s.", res->status_code.c_str());
				m_logger->error("Failed to parse result of insertTable. %s",
						GetParseError_En(doc.GetParseError()));
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
	} catch (exception& ex) {
		m_logger->error("Failed to insert into table %s: %s", tableName.c_str(), ex.what());
		throw;
	}
}

/**
 * Update data into an arbitrary table
 *
 * @param tableName	The name of the table into which data will be added
 * @param values	The values to insert into the table
 * @param query		The conditions to match the updated rows
 * @return int		The number of rows updated
 */
int StorageClient::updateTable(const string& tableName, const InsertValues& values, const Query& query)
{
	try {
		ostringstream convert;

		convert << "{ \"condition\" : ";
		convert << query.toJSON();
		convert << ", \"values\" : ";
		convert << values.toJSON();
		convert << " }";
		char url[128];
		snprintf(url, sizeof(url), "/storage/table/%s", tableName.c_str());
		auto res = m_client->request("PUT", url, convert.str());
		if (res->status_code.compare("200 OK") == 0)
		{
			ostringstream resultPayload;
			resultPayload << res->content.rdbuf();
			Document doc;
			doc.Parse(res->content.string().c_str());
			if (doc.HasParseError())
			{
				m_logger->info("PUT result %s.", res->status_code.c_str());
				m_logger->error("Failed to parse result of insertTable. %s",
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
	} catch (exception& ex) {
		m_logger->error("Failed to update table %s: %s", tableName.c_str(), ex.what());
		throw;
	}
}


