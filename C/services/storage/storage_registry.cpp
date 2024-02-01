/*
 * Fledge storage service.
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <rapidjson/document.h>
#include "rapidjson/stringbuffer.h"
#include <rapidjson/writer.h>
#include "storage_registry.h"
#include "client_http.hpp"
#include "server_http.hpp"
#include "management_api.h"
#include "reading_set.h"
#include "reading.h"
#include "logger.h"
#include "strings.h"
#include "client_http.hpp"
#include <chrono>

#define CHECK_QTIMES	0	// Turn on to check length of time data is queued
#define QTIME_THRESHOLD 3	// Threshold to report long queue times

#define REGISTRY_SLEEP_TIME	5	// Time to sleep in the register process thread
					// between checks for chutdown

using namespace std;
using namespace rapidjson;
using HttpClient = SimpleWeb::Client<SimpleWeb::HTTP>;

/**
 * Worker thread entry point
 */
static void worker(StorageRegistry *registry)
{
	registry->run();
}

/**
 * StorageRegistry constructor
 *
 * The storage registry holds registrations for other micro services
 * that wish to receive notifications when new data is avialable for
 * a given asset. The interested service registers a URL and an asset
 * code, or * for all assets, that URL will then be called when new
 * data arrives for the particular asset.
 *
 * The service registry maintians a worker thread that is responsible
 * for sending these notifications such that the main flow of data into
 * the storage layer is minimally impacted by the registration and
 * delivery of these messages to interested microservices.
 */
StorageRegistry::StorageRegistry() : m_thread(NULL)
{
	m_running = true;
	m_thread = new thread(worker, this);
}

/**
 * StorageRegistry destructor
 */
StorageRegistry::~StorageRegistry()
{
	m_running = false;
	m_cv.notify_all();
	if (m_thread)
	{
		if (m_thread->joinable())
			m_thread->join();
		delete m_thread;
		m_thread = NULL;
	}
	while (!m_queue.empty())
		m_queue.pop();
	while (!m_tableInsertQueue.empty())
		m_tableInsertQueue.pop();
	while (!m_tableUpdateQueue.empty())
		m_tableUpdateQueue.pop();
	while (!m_tableDeleteQueue.empty())
		m_tableDeleteQueue.pop();
}

/**
 * Process a reading append payload and determine
 * if any microservice has registered an interest
 * in this asset.
 *
 * @param payload	The reading append payload
 */
void
StorageRegistry::process(const string& payload)
{
	if (m_registrations.size() != 0)
	{
		/*
		 * We have some registrations so queue a copy of the payload
		 * to be examined in the thread the send reading notifications
		 * to interested parties.
		 */
		char *data = NULL;
		if ((data = strdup(payload.c_str())) != NULL)
		{
			time_t now = time(0);
			Item item = make_pair(now, data);
			lock_guard<mutex> guard(m_qMutex);
			m_queue.push(item);
			m_cv.notify_all();
		}
	}
}

/**
 * Process a table insert payload and determine
 * if any microservice has registered an interest
 * in this table. Called from StorageApi::commonInsert()
 *
 * @param payload	The table insert payload
 */
void
StorageRegistry::processTableInsert(const string& tableName, const string& payload)
{
	Logger::getLogger()->debug("StorageRegistry::processTableInsert(): tableName=%s, payload=%s", tableName.c_str(), payload.c_str());
	
	if (m_tableRegistrations.size() > 0)
	{
		/*
		 * We have some registrations so queue a copy of the payload
		 * to be examined in the thread the send table notifications
		 * to interested parties.
		 */
		char *table = strdup(tableName.c_str());
		char *data = strdup(payload.c_str());
		
		if (data != NULL && table != NULL)
		{
			time_t now = time(0);
			TableItem item = make_tuple(now, table, data);
			lock_guard<mutex> guard(m_qMutex);
			m_tableInsertQueue.push(item);
			m_cv.notify_all();
		}
	}
}

/**
 * Process a table update payload and determine
 * if any microservice has registered an interest
 * in this table. Called from StorageApi::commonUpdate()
 *
 * @param payload	The table update payload
 */
void
StorageRegistry::processTableUpdate(const string& tableName, const string& payload)
{
	Logger::getLogger()->info("Checking for registered interest in table %s with update %s", tableName.c_str(), payload.c_str());
	
	if (m_tableRegistrations.size() > 0)
	{
		/*
		 * We have some registrations so queue a copy of the payload
		 * to be examined in the thread the send table notifications
		 * to interested parties.
		 */
		char *table = strdup(tableName.c_str());
		char *data = strdup(payload.c_str());
		
		if (data != NULL && table != NULL)
		{
			time_t now = time(0);
			TableItem item = make_tuple(now, table, data);
			lock_guard<mutex> guard(m_qMutex);
			m_tableUpdateQueue.push(item);
			m_cv.notify_all();
		}
	}
}

/**
 * Process a table delete payload and determine
 * if any microservice has registered an interest
 * in this table. Called from StorageApi::commonDelete()
 *
 * @param payload	The table delete payload
 */
void
StorageRegistry::processTableDelete(const string& tableName, const string& payload)
{
	Logger::getLogger()->info("Checking for registered interest in table %s with delete %s", tableName.c_str(), payload.c_str());
	
	if (m_tableRegistrations.size() > 0)
	{
		/*
		 * We have some registrations so queue a copy of the payload
		 * to be examined in the thread the send table notifications
		 * to interested parties.
		 */
		char *table = strdup(tableName.c_str());
		char *data = strdup(payload.c_str());
		
		if (data != NULL && table != NULL)
		{
			time_t now = time(0);
			TableItem item = make_tuple(now, table, data);
			lock_guard<mutex> guard(m_qMutex);
			m_tableDeleteQueue.push(item);
			m_cv.notify_all();
		}
	}
}

/**
 * Handle a registration request from a client of the storage layer
 *
 * @param asset		The asset of interest
 * @param url		The URL to call
 */
void
StorageRegistry::registerAsset(const string& asset, const string& url)
{
	lock_guard<mutex> guard(m_registrationsMutex);
	m_registrations.push_back(pair<string *, string *>(new string(asset), new string(url)));
}

/**
 * Handle a request to remove a registration of interest
 *
 * @param asset		The asset of interest
 * @param url		The URL to call
 */
void
StorageRegistry::unregisterAsset(const string& asset, const string& url)
{
	lock_guard<mutex> guard(m_registrationsMutex);
	for (auto it = m_registrations.begin(); it != m_registrations.end(); )
	{
		if (asset.compare(*(it->first)) == 0 && url.compare(*(it->second)) == 0)
		{
			delete it->first;
			delete it->second;
			it = m_registrations.erase(it);
		}
		else
		{
			++it;
        	}
	}
}

/**
 * Parse a table subscription (un)register JSON payload
 *
 * @param payload	JSON payload describing the interest
 */
TableRegistration* StorageRegistry::parseTableSubscriptionPayload(const string& payload)
{
	Document	doc;
	
	doc.Parse(payload.c_str());
	if (doc.HasParseError())
	{
		Logger::getLogger()->error("StorageRegistry::parseTableSubscriptionPayload(): Parse error in subscription request payload");
		return NULL;
	}
	if (!doc.HasMember("url"))
	{
		Logger::getLogger()->error("StorageRegistry::parseTableSubscriptionPayload(): subscription request doesn't have url field");
		return NULL;
	}
	if (!doc.HasMember("key"))
	{
		Logger::getLogger()->error("StorageRegistry::parseTableSubscriptionPayload(): subscription request doesn't have url field");
		return NULL;
	}
	if (!doc.HasMember("operation"))
	{
		Logger::getLogger()->error("StorageRegistry::parseTableSubscriptionPayload(): subscription request doesn't have url field");
		return NULL;
	}

	TableRegistration *reg = new TableRegistration;
	
	reg->url = doc["url"].GetString();
	reg->key = doc["key"].GetString();
	reg->operation = doc["operation"].GetString();
	
	if (reg->key.size())
	{
		if (!doc.HasMember("values") || !doc["values"].IsArray())
		{
			Logger::getLogger()->error("Subscription request" \
					" doesn't have a proper values field, payload=%s", payload.c_str());
			delete reg;
			return NULL;
		}
		for (auto & v : doc["values"].GetArray())
	    		reg->keyValues.emplace_back(v.GetString());
	}

	return reg;
}

/**
 * Handle a registration request for a table from a client of the storage layer
 *
 * @param table		The table of interest
 * @param payload	JSON payload describing the interest
 */
void
StorageRegistry::registerTable(const string& table, const string& payload)
{
	TableRegistration *reg = parseTableSubscriptionPayload(payload); 

	if (!reg)
	{
		Logger::getLogger()->error("Unable to register invalid Registration entry for table %s, payload %s",
				table.c_str(), payload.c_str());
		return;
	}

	lock_guard<mutex> guard(m_tableRegistrationsMutex);
	Logger::getLogger()->info("Adding registration entry for table %s", table.c_str());
	m_tableRegistrations.push_back(pair<string *, TableRegistration *>(new string(table), reg));
}

/**
 * Handle a request to remove a registration of interest in a table
 *
 * @param table		The table of interest
 * @param payload	JSON payload describing the interest
 */
void
StorageRegistry::unregisterTable(const string& table, const string& payload)
{
	TableRegistration *reg = parseTableSubscriptionPayload(payload);

	if (!reg)
	{
		Logger::getLogger()->info("Invalid Registration entry for table %s, payload %s",
				table.c_str(), payload.c_str());
		return;
	}

	lock_guard<mutex> guard(m_tableRegistrationsMutex);
	
	Logger::getLogger()->info("%d entries registered interest in table operations", m_tableRegistrations.size());
	bool found = false;
	for (auto it = m_tableRegistrations.begin(); found == false && it != m_tableRegistrations.end(); )
	{
		TableRegistration *reg_it = it->second;
		if (table.compare(*(it->first)) == 0 && 
			reg->url.compare(reg_it->url)==0 &&
			reg->key.compare(reg_it->key)==0 &&
			reg->operation.compare(reg_it->operation)==0)
		{
			// Either no key is to be matched or a key is to be matched against a possible set of values
			if (reg->key.size()==0 || (reg->key.size()>0 && reg->keyValues == reg_it->keyValues))
			{
				delete it->first;
				delete it->second;
				it = m_tableRegistrations.erase(it);
				Logger::getLogger()->info("Removed registration for table %s and url %s", table, reg->key.c_str());
				found = true;
			}
			else
			{
				++it;
    			}
		}
		else
		{
			++it;
    		}
	}
	if (!found)
	{
		Logger::getLogger()->warn(
				"Failed to remove subscription for table '%s' using key '%s' with operation '%s' and url '%s'",
				table.c_str(), reg->key.c_str(), reg->operation.c_str(), reg->url.c_str());
	}
	delete reg;
}


/**
 * The worker function that processes the queue of payloads
 * that may need to be sent to subscribers.
 */
void
StorageRegistry::run()
{	
	while (m_running)
	{
		char *data = NULL;
#if CHECK_QTIMES
		time_t qTime;
#endif
		{
			unique_lock<mutex> mlock(m_cvMutex);
			while (m_queue.size() == 0 && m_tableInsertQueue.size() == 0 && m_tableUpdateQueue.size() == 0 && m_tableDeleteQueue.size() == 0)
			{
				m_cv.wait_for(mlock, std::chrono::seconds(REGISTRY_SLEEP_TIME));
				if (!m_running)
				{
					return;
				}
			}
			
			while (!m_queue.empty())
			{
				Item item = m_queue.front();
				m_queue.pop();
				data = item.second;
#if CHECK_QTIMES
				qTime = item.first;
#endif
				if (data)
				{
#if CHECK_QTIMES
					if (time(0) - qTime > QTIME_THRESHOLD)
					{
						Logger::getLogger()->error("Readings data has been queued for %d seconds to be sent to registered party", (time(0) - qTime));
					}
#endif
					processPayload(data);
					free(data);
				}
			}
			
			while (!m_tableInsertQueue.empty())
			{
				char *tableName = NULL;
				
				TableItem item = m_tableInsertQueue.front();
				m_tableInsertQueue.pop();
				tableName = get<1>(item);
				data = get<2>(item);
#if CHECK_QTIMES
				qTime = item.first;
#endif
				if (tableName && data)
				{
#if CHECK_QTIMES
					if (time(0) - qTime > QTIME_THRESHOLD)
					{
						Logger::getLogger()->error("Table insert data has been queued for %d seconds to be sent to registered party", (time(0) - qTime));
					}
#endif
					processInsert(tableName, data);
					free(tableName);
					free(data);
				}
			}

			while (!m_tableUpdateQueue.empty())
			{
				char *tableName = NULL;
				
				TableItem item = m_tableUpdateQueue.front();
				m_tableUpdateQueue.pop();
				tableName = get<1>(item);
				data = get<2>(item);
#if CHECK_QTIMES
				qTime = item.first;
#endif
				if (tableName && data)
				{
#if CHECK_QTIMES
					if (time(0) - qTime > QTIME_THRESHOLD)
					{
						Logger::getLogger()->error("Table update data has been queued for %d seconds to be sent to registered party", (time(0) - qTime));
					}
#endif
					processUpdate(tableName, data);
					free(tableName);
					free(data);
				}
			}

			while (!m_tableDeleteQueue.empty())
			{
				char *tableName = NULL;
				
				TableItem item = m_tableDeleteQueue.front();
				m_tableDeleteQueue.pop();
				tableName = get<1>(item);
				data = get<2>(item);
#if CHECK_QTIMES
				qTime = item.first;
#endif
				if (tableName && data)
				{
#if CHECK_QTIMES
					if (time(0) - qTime > QTIME_THRESHOLD)
					{
						Logger::getLogger()->error("Table delete data has been queued for %d seconds to be sent to registered party", (time(0) - qTime));
					}
#endif
					processDelete(tableName, data);
					free(tableName);
					free(data);
				}
			}
		}
	}
}

/**
 * Process an incoming payload and distribute as required to registered
 * services
 *
 * @param payload	The payload to potentially distribute
 */
void
StorageRegistry::processPayload(char *payload)
{
bool allDone = true;

	lock_guard<mutex> guard(m_registrationsMutex);

	// First of all deal with those that registered for all assets
	for (REGISTRY::const_iterator it = m_registrations.cbegin(); it != m_registrations.cend(); it++)
	{
		if (it->first->compare("*") == 0)
		{
			sendPayload(*(it->second), payload);
		}
		else
		{
			allDone = false;
		}
	}
	if (allDone)
	{
		// No registrations for individual assets, no need to parse payload
		return;
	}
	for (REGISTRY::const_iterator it = m_registrations.cbegin(); it != m_registrations.cend(); it++)
	{
		if (it->first->compare("*") != 0)
		{
			try {
				filterPayload(*(it->second), payload, *(it->first));
			} catch (const exception& e) {
				Logger::getLogger()->error("filterPayload: exception %s", e.what());
			}
		}
	}
}


/**
 * Send the copy of the payload to the given URL
 *
 * @param url		The URL to send the payload to
 * @param payload	The payload to send
 */
void
StorageRegistry::sendPayload(const string& url, const char *payload)
{
	size_t found = url.find_first_of("://");
	size_t found1 = url.find_first_of("/", found + 3);
	string hostport = url.substr(found+3, found1 - found - 3);
	string resource = url.substr(found1);
	HttpClient client(hostport);
	try {
		client.request("POST", resource, payload);
	} catch (const exception& e) {
		Logger::getLogger()->error("sendPayload: exception %s sending reading data to interested party %s", e.what(), url.c_str());
	}
}

/**
 * Send a filtered copy of the payload to the given URL
 *
 * @param url		The URL to send the payload to
 * @param payload	The payload to send
 * @param asset		The asset code to filter
 */
void
StorageRegistry::filterPayload(const string& url, char *payload, const string& asset)
{
ostringstream convert;

	size_t found = url.find_first_of("://");
	size_t found1 = url.find_first_of("/", found + 3);
	string hostport = url.substr(found+3, found1 - found - 3);
	string resource = url.substr(found1);

	// Filter the payload to include just the one asset
	Document doc;
	doc.Parse(payload);
	if (doc.HasParseError())
	{
		Logger::getLogger()->error("filterPayload: Parse error in payload");
		return;
	}
	if (!doc.HasMember("readings"))
	{
		Logger::getLogger()->error("filterPayload: payload has no readings object");
		return;
	}
	const Value& readings = doc["readings"];
	if (!readings.IsArray())
	{
		Logger::getLogger()->error("filterPayload: payload readings object is not an array");
		return;
	}
	convert << "{ \"readings\" : [ ";
	int count = 0;
	/*
	 * Loop over the readings and create a reading object for
	 * each, check if it matches the asset name and incldue in the
	 * new payload if it does. In eother case free that object
	 * immediately to reduce the memory requirement.
	 */
	for (auto& reading : readings.GetArray())
	{
		if (reading.IsObject())
		{
			JSONReading *value = new JSONReading(reading);
			if (value->getAssetName().compare(asset) == 0)
			{
				if (count)
					convert << ",";
				count++;
				convert << value->toJSON();
			}
			delete value;
		}
	}
	
	convert << "] }";

	/*
	 * Check if any assets inthe filtered payload
	 */
	if (count == 0)
	{
		// Nothing to send
		return;
	}

	HttpClient client(hostport);
	try {
		client.request("POST", resource, convert.str());
	} catch (const exception& e) {
		Logger::getLogger()->error("filterPayload: exception %s sending reading data to interested party %s", e.what(), url.c_str());
	}
}

/**
 * Process an incoming payload and distribute as required to registered
 * services
 *
 * @param payload	The payload to potentially distribute
 */
void
StorageRegistry::processInsert(char *tableName, char *payload)
{
	Logger::getLogger()->debug("StorageRegistry::processInsert(): Handling for table:%s, payload=%s", tableName, payload);
	Logger::getLogger()->debug("StorageRegistry::processInsert(): m_tableRegistrations.size()=%d", m_tableRegistrations.size());
	
	Document	payloadDoc;
	
	payloadDoc.Parse(payload);
	if (payloadDoc.HasParseError())
	{
		Logger::getLogger()->error("Internal error unable to parse payload for insert into table %s, payload is %s", tableName, payload);
		return;
	}

	lock_guard<mutex> guard(m_tableRegistrationsMutex);
	for (auto & reg : m_tableRegistrations)
	{
		if (reg.first->compare(tableName) != 0)
			continue;

		TableRegistration *tblreg = reg.second;

		// If key is empty string, no need to match key/value pair in payload
		// Also operation must be "insert" for initial implementation
		if (tblreg->operation.compare("insert") != 0)
		{
			continue;
		}

		if (tblreg->key.size() == 0)
		{
			sendPayload(tblreg->url, payload);
		}
		else
		{
			if (payloadDoc.HasMember("inserts") && payloadDoc["inserts"].IsArray())
			{
				// We have multiple inserts in the payload, parse each one and send
				// only the insert for which the key has been registered
				Value &inserts = payloadDoc["inserts"];
				for (Value::ConstValueIterator iter = inserts.Begin();
						iter != inserts.End(); ++iter)
				{
					if (iter->HasMember(tblreg->key.c_str()))
					{
						string payloadKeyValue = (*iter)[tblreg->key.c_str()].GetString();
						if (std::find(tblreg->keyValues.begin(), tblreg->keyValues.end(), payloadKeyValue) != tblreg->keyValues.end())
						{
							StringBuffer buffer;
							Writer<StringBuffer> writer(buffer);
							iter->Accept(writer);

							const char *output = buffer.GetString();
							sendPayload(tblreg->url, output);
						}
					}
				}
			}
			else
			{
				if (payloadDoc.HasMember(tblreg->key.c_str()) && payloadDoc[tblreg->key.c_str()].IsString())
				{
					string payloadKeyValue = payloadDoc[tblreg->key.c_str()].GetString();
					if (std::find(tblreg->keyValues.begin(), tblreg->keyValues.end(), payloadKeyValue) != tblreg->keyValues.end())
					{
						sendPayload(tblreg->url, payload);
					}
				}
			}
		}
	}
}

/**
 * Process an incoming payload and distribute as required to registered
 * services
 *
 * @param payload	The payload to potentially distribute
 */
void
StorageRegistry::processUpdate(char *tableName, char *payload)
{
	Document	doc;

	doc.Parse(payload);
	if (doc.HasParseError())
	{
		Logger::getLogger()->error("Unable to parse table update payload for table %s, request is %s", tableName, payload);
		return;
	}

	lock_guard<mutex> guard(m_tableRegistrationsMutex);
	for (auto & reg : m_tableRegistrations)
	{
		if (reg.first->compare(tableName) != 0)
			continue;

		TableRegistration *tblreg = reg.second;

		// If key is empty string, no need to match key/value pair in payload
		if (tblreg->operation.compare("update") != 0)
		{
			continue;
		}

		if (tblreg->key.empty())
		{
			// No key to match, send all updates to table
			sendPayload(tblreg->url, payload);
		}
		else
		{
			if (doc.HasMember("updates") && doc["updates"].IsArray())
			{
				// Multiple updates in a single call
				Value &updates = doc["updates"];
				for (Value::ConstValueIterator iter = updates.Begin();
						iter != updates.End(); ++iter)
				{
					const Value& where = (*iter)["where"];
					if (where.HasMember("column") && where["column"].IsString() &&
							where.HasMember("value") && where["value"].IsString())
					{
						string updateKey = where["column"].GetString();
						string keyValue = where["value"].GetString();
						if (updateKey.compare(tblreg->key) == 0 &&
								std::find(tblreg->keyValues.begin(), tblreg->keyValues.end(), keyValue)
								!= tblreg->keyValues.end())
						{
							if (iter->HasMember("values"))
							{
								const Value& values = (*iter)["values"];
								StringBuffer buffer;
								Writer<StringBuffer> writer(buffer);
								values.Accept(writer);

								const char *output = buffer.GetString();
								sendPayload(tblreg->url, output);
							}
							else if (iter->HasMember("expressions"))
							{
								const Value& expressions = (*iter)["expressions"];
								for (Value::ConstValueIterator expr = expressions.Begin();
										expr != expressions.End(); ++expr)
								{
									StringBuffer buffer;
									Writer<StringBuffer> writer(buffer);
									expr->Accept(writer);
	
									const char *output = buffer.GetString();
									sendPayload(tblreg->url, output);
								}
							}
						}
					}
				}
			}
			else if (doc.HasMember("where") && doc["where"].IsObject())
			{
				const Value& where = doc["where"];
				if (where.HasMember("column") && where["column"].IsString() &&
						where.HasMember("value") && where["value"].IsString())
				{
					string updateKey = where["column"].GetString();
					string keyValue = where["value"].GetString();
					if (updateKey.compare(tblreg->key) == 0 &&
							std::find(tblreg->keyValues.begin(), tblreg->keyValues.end(), keyValue)
							!= tblreg->keyValues.end())
					{
						if (doc.HasMember("values"))
						{
							const Value& values = doc["values"];
							StringBuffer buffer;
							Writer<StringBuffer> writer(buffer);
							values.Accept(writer);

							const char *output = buffer.GetString();
							sendPayload(tblreg->url, output);
						}
						else if (doc.HasMember("expressions"))
						{
							const Value& expressions = doc["expressions"];
							for (Value::ConstValueIterator expr = expressions.Begin();
									expr != expressions.End(); ++expr)
							{
								StringBuffer buffer;
								Writer<StringBuffer> writer(buffer);
								expr->Accept(writer);

								const char *output = buffer.GetString();
								sendPayload(tblreg->url, output);
							}
						}
					}
				}
			}
		}
	}
}

/**
 * Process an incoming payload and distribute as required to registered
 * services
 *
 * @param payload	The payload to potentially distribute
 */
void
StorageRegistry::processDelete(char *tableName, char *payload)
{
	Document	doc;
	bool allRows = false;

	if (! *payload) // Empty
	{
		allRows = true;
	}
	else
	{
		doc.Parse(payload);
		if (doc.HasParseError())
		{
			Logger::getLogger()->error("Unable to parse table delete payload for table %s, request is %s", tableName, payload);
			return;
		}
	}

	lock_guard<mutex> guard(m_tableRegistrationsMutex);
	for (auto & reg : m_tableRegistrations)
	{
		if (reg.first->compare(tableName) != 0)
			continue;

		TableRegistration *tblreg = reg.second;

		// If key is empty string, no need to match key/value pair in payload
		if (tblreg->operation.compare("delete") != 0)
		{
			continue;
		}
		if (allRows)
		{
			sendPayload(tblreg->url, payload);
		}
		else if (tblreg->key.empty())
		{
			// No key to match, send all updates to table
			sendPayload(tblreg->url, payload);
		}
		else
		{
			if (doc.HasMember("where") && doc["where"].IsObject())
			{
				const Value& where = doc["where"];
				if (where.HasMember("column") && where["column"].IsString() &&
						where.HasMember("value") && where["value"].IsString())
				{
					string updateKey = where["column"].GetString();
					string keyValue = where["value"].GetString();
					if (updateKey.compare(tblreg->key) == 0 &&
							std::find(tblreg->keyValues.begin(), tblreg->keyValues.end(), keyValue)
							!= tblreg->keyValues.end())
					{
						StringBuffer buffer;
						Writer<StringBuffer> writer(buffer);
						where.Accept(writer);

						const char *output = buffer.GetString();
						sendPayload(tblreg->url, output);
					}
				}
			}
		}
	}
}

/**
 * Test function to add some dummy/test table subscriptions
 */
void StorageRegistry::insertTestTableReg()
{
	string table1("log");
	string payload1 = R"***( {"url": "http://localhost:8081/dummyTableNotifyUrl", "key": "code", "values":["CONAD", "PURGE", "CONCH", "FSTOP", "SRVRG"], "operation": "insert"} )***";

	string table2("asset_tracker");
	string payload2 = R"***( {"url": "http://localhost:8081/dummyTableNotifyUrl2", "key": "", "operation": "insert"} )***";

	string table3("asset_tracker");
	string payload3 = R"***( {"url": "http://localhost:8081/dummyTableNotifyUrl3", "key": "event", "values":["Ingest", "Filter"], "operation": "insert"} )***";
	
	Logger::getLogger()->error("StorageRegistry::insertTestTableReg(): table=%s, payload=%s", table1.c_str(), payload1.c_str());
	registerTable(table1, payload1);

	Logger::getLogger()->error("StorageRegistry::insertTestTableReg(): table=%s, payload=%s", table2.c_str(), payload2.c_str());
	registerTable(table2, payload2);

	Logger::getLogger()->error("StorageRegistry::insertTestTableReg(): table=%s, payload=%s", table3.c_str(), payload3.c_str());
	registerTable(table3, payload3);
}

/**
 * Test function to remove a dummy/test table subscription
 *
 * @param n		The subscription number to remove
 */
void StorageRegistry::removeTestTableReg(int n)
{
	string table1("log");
	string payload1 = R"***( {"url": "http://localhost:8081/dummyTableNotifyUrl", "key": "code", "values":["CONAD", "PURGE", "CONCH", "FSTOP", "SRVRG"], "operation": "insert"} )***";

	string table2("asset_tracker");
	string payload2 = R"***( {"url": "http://localhost:8081/dummyTableNotifyUrl2", "key": "", "operation": "insert"} )***";

	string table3("asset_tracker");
	string payload3 = R"***( {"url": "http://localhost:8081/dummyTableNotifyUrl3", "key": "event", "values":["Ingest", "Filter"], "operation": "insert"} )***";
	
	switch(n)
	{
		case 1:
			unregisterTable(table1, payload1);
			Logger::getLogger()->error("StorageRegistry::removeTestTableReg(): table=%s, payload=%s", table1.c_str(), payload1.c_str());
			break;

		case 2:
			unregisterTable(table2, payload2);
			Logger::getLogger()->error("StorageRegistry::removeTestTableReg(): table=%s, payload=%s", table2.c_str(), payload2.c_str());
			break;

		case 3:
			unregisterTable(table3, payload3);
			Logger::getLogger()->error("StorageRegistry::removeTestTableReg(): table=%s, payload=%s", table3.c_str(), payload3.c_str());
			break;

		default:
			Logger::getLogger()->error("StorageRegistry::removeTestTableReg(): unhandled value n=%d", n);
			break;
	}
}


