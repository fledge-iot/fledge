/*
 * FogLAMP storage service.
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <rapidjson/document.h>
#include "storage_registry.h"
#include "client_http.hpp"
#include "server_http.hpp"
#include "management_api.h"
#include "reading_set.h"
#include "reading.h"
#include "logger.h"
#include "strings.h"
#include "client_http.hpp"

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
 * The servce registry maintians a worker thread that is responsible
 * for sending these notifications such that the main flow of data into
 * the storage layer is minimally impacted by the registration and
 * delivery of these messages to interested microservices.
 */
StorageRegistry::StorageRegistry()
{
	m_thread = new thread(worker, this);
}

/**
 * StorageRegistry destructor
 */
StorageRegistry::~StorageRegistry()
{
	m_running = false;
	m_thread->join();
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
			lock_guard<mutex> guard(m_qMutex);
			m_queue.push(data);
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
 * The worker function that processes the queue of payloads
 * that may need to be sent to subscribers.
 */
void
StorageRegistry::run()
{
	m_running = true;
	while (m_running)
	{
		char *data = NULL;
		{
			unique_lock<mutex> mlock(m_cvMutex);
			m_cv.wait(mlock);
			data = m_queue.front();
			m_queue.pop();
		}
		if (data)
		{
			processPayload(data);
			free(data);
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
StorageRegistry::sendPayload(const string& url, char *payload)
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
		Logger::getLogger()->error("filterPayload: nothing to send, %s, %s", asset.c_str(), payload);
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
