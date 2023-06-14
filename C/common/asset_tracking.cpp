/*
 * Fledge asset tracking related
 *
 * Copyright (c) 2019 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Amandeep Singh Arora
 */

#include <logger.h>
#include <asset_tracking.h>
#include <config_category.h>

using namespace std;


AssetTracker *AssetTracker::instance = 0;

/**
 * Worker thread entry point
 */
static void worker(void *arg)
{
	AssetTracker *tracker = (AssetTracker *)arg;
	tracker->workerThread();
}

/**
 * Get asset tracker singleton instance for the current south service
 *
 * @return	Singleton asset tracker instance
 */
AssetTracker *AssetTracker::getAssetTracker()
{
	return instance;
}

/**
 * AssetTracker class constructor
 *
 * @param mgtClient		Management client object for this south service
 * @param service  		Service name
 */
AssetTracker::AssetTracker(ManagementClient *mgtClient, string service) 
	: m_mgtClient(mgtClient), m_service(service)
{
	instance = this;
	m_shutdown = false;
	m_storageClient = NULL;
	m_thread = new thread(worker, this);

	try {
		// Find out the name of the fledge service
		ConfigCategory category = mgtClient->getCategory("service");
		if (category.itemExists("name"))
		{
			m_fledgeName = category.getValue("name");
		}
	} catch (exception& ex) {
		Logger::getLogger()->error("Unable to fetch the service category, %s", ex.what());
	}

	try {
		// Get a handle on the storage layer
		ServiceRecord storageRecord("Fledge Storage");
		if (!m_mgtClient->getService(storageRecord))
		{
			Logger::getLogger()->fatal("Unable to find storage service");
			return;
		}
		Logger::getLogger()->info("Connect to storage on %s:%d",
				storageRecord.getAddress().c_str(),
				storageRecord.getPort());

		
		m_storageClient = new StorageClient(storageRecord.getAddress(),
						storageRecord.getPort());
	} catch (exception& ex) {
		Logger::getLogger()->error("Failed to create storage client", ex.what());
	}

}

/**
 * Destructor for the asset tracker. We must make sure any pending
 * tuples are written out before the asset tracker is destroyed.
 */
AssetTracker::~AssetTracker()
{
	m_shutdown = true;
	// Signal the worker thread to flush the queue
	{
		unique_lock<mutex> lck(m_mutex);
		m_cv.notify_all();
	}
	while (m_pending.size())
	{
		// Wait for pending queue to drain
		this_thread::sleep_for(chrono::milliseconds(10));
	}
	if (m_thread)
	{
		m_thread->join();
		delete m_thread;
		m_thread = NULL;
	}

	if (m_storageClient)
	{
		delete m_storageClient;
	}
}

/**
 * Fetch all asset tracking tuples from DB and populate local cache
 *
 * Return the vector of deprecated asset names
 *
 * @param plugin  	Plugin name
 * @param event  	Event name
 */
void AssetTracker::populateAssetTrackingCache(string /*plugin*/, string /*event*/)
{
	try {
		std::vector<AssetTrackingTuple*>& vec = m_mgtClient->getAssetTrackingTuples(m_service);
		for (AssetTrackingTuple* & rec : vec)
		{
			assetTrackerTuplesCache.insert(rec);
		}
		delete (&vec);
	}
	catch (...)
	{
		Logger::getLogger()->error("Failed to populate asset tracking tuples' cache");
		return;
	}

	return;
}

/**
 * Check local cache for a given asset tracking tuple
 *
 * @param tuple		Tuple to find in cache
 * @return			Returns whether tuple is present in cache
 */
bool AssetTracker::checkAssetTrackingCache(AssetTrackingTuple& tuple)	
{
	AssetTrackingTuple *ptr = &tuple;
	std::unordered_set<AssetTrackingTuple*>::const_iterator it = assetTrackerTuplesCache.find(ptr);
	if (it == assetTrackerTuplesCache.end())
	{
		return false;
	}
	else
		return true;
}

/**
 * Lookup tuple in the asset tracker cache
 *
 * @param tuple		The tuple to lookup
 * @return		NULL if the tuple is not in the cache or the tuple from the cache
 */
AssetTrackingTuple* AssetTracker::findAssetTrackingCache(AssetTrackingTuple& tuple)	
{
	AssetTrackingTuple *ptr = &tuple;
	std::unordered_set<AssetTrackingTuple*>::const_iterator it = assetTrackerTuplesCache.find(ptr);
	if (it == assetTrackerTuplesCache.end())
	{
		return NULL;
	}
	else
	{
		return *it;
	}
}

/**
 * Add asset tracking tuple via microservice management API and in cache
 *
 * @param tuple		New tuple to add in DB and in cache
 */
void AssetTracker::addAssetTrackingTuple(AssetTrackingTuple& tuple)
{
	std::unordered_set<AssetTrackingTuple*>::const_iterator it = assetTrackerTuplesCache.find(&tuple);
	if (it == assetTrackerTuplesCache.end())
	{
		AssetTrackingTuple *ptr = new AssetTrackingTuple(tuple);
		queue(ptr);
		assetTrackerTuplesCache.insert(ptr);
		Logger::getLogger()->info("addAssetTrackingTuple(): Added tuple to cache: '%s'", tuple.assetToString().c_str());
	}
}

/**
 * Add asset tracking tuple via microservice management API and in cache
 *
 * @param plugin	Plugin name
 * @param asset		Asset name
 * @param event		Event name
 */
void AssetTracker::addAssetTrackingTuple(string plugin, string asset, string event)
{
	// in case of "Filter" event, 'plugin' input argument is category name, so remove service name (prefix) & '_' from it
	if (event == string("Filter"))
	{
		string pattern  = m_service + "_";
		if (plugin.find(pattern) != string::npos)
			plugin.erase(plugin.begin(), plugin.begin() + m_service.length() + 1);

	}
	
	AssetTrackingTuple tuple(m_service, plugin, asset, event);
	addAssetTrackingTuple(tuple);
}

/**
 * Return the name of the service responsible for particular event of the named asset
 *
 * @param event	The event of interest
 * @param asset	The asset we are interested in
 * @return string	The service name of the service that ingests the asset
 * @throws exception 	If the service could not be found
 */
string AssetTracker::getService(const std::string& event, const std::string& asset)
{
	// Fetch all asset tracker records
	std::vector<AssetTrackingTuple*>& vec = m_mgtClient->getAssetTrackingTuples();
	string foundService;
	for (AssetTrackingTuple* &rec : vec)
	{
		// Return first service name with given asset and event
		if (rec->m_assetName == asset && rec->m_eventName == event)
		{
			foundService = rec->m_serviceName;
			break;
		}
	}

	delete (&vec);

	// Return found service or raise an exception
	if (foundService != "")
	{
		return foundService;
	}
	else
	{
		Logger::getLogger()->error("No service found for asset '%s' and event '%s'",
					event.c_str(),
					asset.c_str());
		throw runtime_error("Fetching service for asset not yet implemented");
	}
}

/**
 * Constructor for an asset tracking tuple table
 */
AssetTrackingTable::AssetTrackingTable()
{
}

/**
 * Destructor for asset tracking tuple table
 */
AssetTrackingTable::~AssetTrackingTable()
{
	for (auto t : m_tuples)
	{
		delete t.second;
	}
}

/**
 * Add a tuple to an asset tracking table
 *
 * @param tuple	Pointer to the asset tracking tuple to add
 */
void	AssetTrackingTable::add(AssetTrackingTuple *tuple)
{
	auto ret = m_tuples.insert(pair<string, AssetTrackingTuple *>(tuple->getAssetName(), tuple));
	if (ret.second == false)
		delete tuple;	// Already exists
}

/**
 * Find the named asset tuple and return a pointer to te asset
 *
 * @param name	The name of the asset to lookup
 * @return AssetTrackingTupple* 	The matchign tuple or NULL
 */
AssetTrackingTuple *AssetTrackingTable::find(const string& name)
{
	auto ret = m_tuples.find(name);
	if (ret != m_tuples.end())
		return ret->second;
	return NULL;
}

/**
 * Remove an asset tracking tuple from the table
 */
void AssetTrackingTable::remove(const string& name)
{
	auto ret = m_tuples.find(name);
	if (ret != m_tuples.end())
	{
		m_tuples.erase(ret);
		delete ret->second;	// Free the tuple
	}
}

/**
 * Queue an asset tuple for writing to the database.
 */
void AssetTracker::queue(AssetTrackingTuple *tuple)
{
	unique_lock<mutex> lck(m_mutex);
	m_pending.push(tuple);
	m_cv.notify_all();
}

/**
 * The worker thread that will flush any pending asset tuples to
 * the database.
 */
void AssetTracker::workerThread()
{
	unique_lock<mutex> lck(m_mutex);
	while (m_pending.empty() && m_shutdown == false)
	{
		m_cv.wait_for(lck, chrono::milliseconds(500));
		processQueue();
	}
	// Process any items left in the queue at shutdown
	processQueue();
}

/**
 * Process the queue of asset tracking tuple
 */
void AssetTracker::processQueue()
{
vector<InsertValues>	values;
static bool warned = false;

	while (!m_pending.empty())
	{
		AssetTrackingTuple *tuple = m_pending.front();
		// Write the tuple - ideally we would like a bulk update here or to go direct to the
		// database. However we need the Fledge service name for that, which is now in
		// the member variable m_fledgeName
		if (!m_storageClient)
		{
			// Fall back to using interface to the core
			if (!warned)
				Logger::getLogger()->warn("Asset tracker falling back to core API");
			warned = true;
			bool rv = m_mgtClient->addAssetTrackingTuple(tuple->m_serviceName, tuple->m_pluginName, tuple->m_assetName, tuple->m_eventName);
		}
		else
		{
			InsertValues iValue;
			iValue.push_back(InsertValue("asset", tuple->m_assetName));
			iValue.push_back(InsertValue("event", tuple->m_eventName));
			iValue.push_back(InsertValue("service", tuple->m_serviceName));
			iValue.push_back(InsertValue("fledge", m_fledgeName));
			iValue.push_back(InsertValue("plugin", tuple->m_pluginName));
			values.push_back(iValue);
		}
		m_pending.pop();
	}
	if (m_storageClient)
	{
		int n_rows = m_storageClient->insertTable("asset_tracker", values);
		if (n_rows != values.size())
		{
			Logger::getLogger()->warn("The asset tracker failed to insert all records %d of %d inserted",
					n_rows, values.size());
		}
	}
}
