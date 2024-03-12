/*
 * Fledge asset tracking related
 *
 * Copyright (c) 2019 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Amandeep Singh Arora, Massimiliano Pinto
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
	: m_mgtClient(mgtClient), m_service(service), m_updateInterval(MIN_ASSET_TRACKER_UPDATE)
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
		m_storageClient = NULL;
	}

	for (auto& item : assetTrackerTuplesCache)
	{
		delete item;
	}
	assetTrackerTuplesCache.clear();

	for (auto& store : storageAssetTrackerTuplesCache)
	{
		delete store.first;
	}
	storageAssetTrackerTuplesCache.clear();
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
			assetTrackerTuplesCache.emplace(rec);
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

		assetTrackerTuplesCache.emplace(ptr);

		queue(ptr);

		Logger::getLogger()->debug("addAssetTrackingTuple(): Added tuple to cache: '%s'", tuple.assetToString().c_str());
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
void AssetTracker::queue(TrackingTuple *tuple)
{
	unique_lock<mutex> lck(m_mutex);
	m_pending.emplace(tuple);
	m_cv.notify_all();
}

/**
 * Set the update interval for the asset tracker.
 *
 * @param interval The number of milliseconds between update of the asset tracker
 * @return bool	Was the update accepted
 */
bool AssetTracker::tune(unsigned long interval)
{
	unique_lock<mutex> lck(m_mutex);
	if (interval >= MIN_ASSET_TRACKER_UPDATE)
	{
		m_updateInterval = interval;
	}
	else
	{
		Logger::getLogger()->error("Attempt to set asset tracker update to less than minimum interval");
		return false;
	}
	return true;
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
		m_cv.wait_for(lck, chrono::milliseconds(m_updateInterval));
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
		// Get first element as TrackingTuple calss
		TrackingTuple *tuple = m_pending.front();

		// Write the tuple - ideally we would like a bulk update here or to go direct to the
		// database. However we need the Fledge service name for that, which is now in
		// the member variable m_fledgeName

		bool warn = warned;
		// Call class specialised processData routine:
		// - 1 Insert asset tracker data via Fledge API as fallback
		// or
		// - get values for direct DB operation

		InsertValues iValue = tuple->processData(m_storageClient != NULL,
							m_mgtClient,
							warn,
							m_fledgeName);
		warned = warn;

		// Bulk DB insert when queue is empty
		if (iValue.size() > 0)
		{
			values.push_back(iValue);
		}

		// Remove element
		m_pending.pop();
	}

	// Queue processed, bulk direct DB data insert could be done
	if (m_storageClient && values.size() > 0)
	{
                // Bulk DB insert
		int n_rows = m_storageClient->insertTable("asset_tracker", values);
		if (n_rows != values.size())
		{
			Logger::getLogger()->warn("The asset tracker failed to insert all records %d of %d inserted",
					n_rows, values.size());
		}
	}
}

/**
 * Fetch all storage asset tracking tuples from DB and populate local cache
 *
 * Return the vector of deprecated asset names
 *
 */
void AssetTracker::populateStorageAssetTrackingCache()
{

	try {
		std::vector<StorageAssetTrackingTuple*>& vec =
			(std::vector<StorageAssetTrackingTuple*>&) m_mgtClient->getStorageAssetTrackingTuples(m_service);

		for (StorageAssetTrackingTuple* & rec : vec)
		{
			set<string> setOfDPs = getDataPointsSet(rec->m_datapoints);
			if (setOfDPs.size() == 0)
			{
				Logger::getLogger()->warn("%s:%d Datapoints unavailable for service %s ",
							__FUNCTION__,
							__LINE__,
							m_service.c_str());
			}
			// Add item into cache
			storageAssetTrackerTuplesCache.emplace(rec, setOfDPs);
		}
		delete (&vec);
	}
	catch (...)
	{
		Logger::getLogger()->error("%s:%d Failed to populate storage asset " \
					"tracking tuples' cache",
					__FUNCTION__,
					__LINE__);
		return;
	}

	return;
}

//This function takes a string of datapoints in comma-separated format and returns
//set of string datapoint values
std::set<std::string> AssetTracker::getDataPointsSet(std::string strDatapoints)
{
	std::set<std::string> tokens;
	stringstream st(strDatapoints);
	std::string temp;

	while(getline(st, temp, ','))
	{
		tokens.insert(temp);
	}

	return tokens;
}

/**
 * Return Plugin Information in the Fledge configuration
 *
 * @return bool True if the plugin info could be obtained
 */
bool AssetTracker::getFledgeConfigInfo()
{
	Logger::getLogger()->error("StorageAssetTracker::getPluginInfo start");
	try {
		string url = "/fledge/category/service";
		if (!m_mgtClient)
		{
			Logger::getLogger()->error("%s:%d, m_mgtClient Ptr is NULL",
						__FUNCTION__,
						__LINE__);
			return false;
		}

		auto res = m_mgtClient->getHttpClient()->request("GET", url.c_str());
		Document doc;
		string response = res->content.string();
		doc.Parse(response.c_str());
		if (doc.HasParseError())
		{
			bool httpError = (isdigit(response[0]) &&
					isdigit(response[1]) &&
					isdigit(response[2]) &&
					response[3]==':');
			Logger::getLogger()->error("%s fetching service record: %s\n",
					httpError?"HTTP error while":"Failed to parse result of",
					response.c_str());
			return false;
		}
		else if (doc.HasMember("message"))
		{
			Logger::getLogger()->error("Failed to fetch /fledge/category/service %s.",
			doc["message"].GetString());
			return false;
		}
		else
		{
			Value& serviceName = doc["name"];
			if (!serviceName.IsObject())
			{
				Logger::getLogger()->error("%s:%d, serviceName is not an object",
							__FUNCTION__,
						       	__LINE__);
				return false;
			}

			if (!serviceName.HasMember("value"))
			{
				Logger::getLogger()->error("%s:%d, serviceName has no member value",
							__FUNCTION__,
							__LINE__);
				return false;

			}
			Value& serviceVal = serviceName["value"];
			if ( !serviceVal.IsString())
			{
				Logger::getLogger()->error("%s:%d, serviceVal is not a string",
							__FUNCTION__,
							__LINE__);
				return false;
			}

			m_fledgeName = serviceVal.GetString();
			Logger::getLogger()->error("%s:%d, m_plugin value = %s",
						__FUNCTION__,
						__LINE__,
						m_fledgeName.c_str());
			return true;
		}

	} catch (const SimpleWeb::system_error &e) {
		Logger::getLogger()->error("Get service failed %s.", e.what());
		return false;
	}

	return false;
}

/** This function takes a StorageAssetTrackingTuple pointer and searches for
 *  it in cache, if found then returns its Deprecated status
 *
 * @param ptr	StorageAssetTrackingTuple* , as key in cache (map)
 * @return bool	Deprecation status
 */
bool AssetTracker::getDeprecated(StorageAssetTrackingTuple* ptr)
{
        StorageAssetCacheMapItr it = storageAssetTrackerTuplesCache.find(ptr);

        if (it == storageAssetTrackerTuplesCache.end())
        {
                Logger::getLogger()->debug("%s:%d :tuple not found in cache",
					__FUNCTION__,
					__LINE__);
                return false;
        }
        else
        {
                return (it->first)->isDeprecated();
        }

        return false;
}

/**
 *  Updates datapoints present in the arg dpSet in the cache
 *
 * @param dpSet		set of datapoints string values to be updated in cache
 * @param ptr		StorageAssetTrackingTuple* , as key in cache (map)
 * Retval void
 */

void AssetTracker::updateCache(std::set<std::string> dpSet, StorageAssetTrackingTuple* ptr)
{
	if(ptr == nullptr)
	{
		Logger::getLogger()->error("%s:%d: StorageAssetTrackingTuple should not be NULL pointer",
					__FUNCTION__,
					__LINE__);
		return;
	}

	StorageAssetCacheMapItr it = storageAssetTrackerTuplesCache.find(ptr);
	// search for the record in cache , if not present, simply update cache and return
	if (it == storageAssetTrackerTuplesCache.end())
	{
		Logger::getLogger()->debug("%s:%d :tuple not found in cache '%s', ptr '%p'",
					__FUNCTION__,
					__LINE__,
					ptr->assetToString().c_str(),
					ptr);

		// Create new tuple, add it to processing queue and to cache
		addStorageAssetTrackingTuple(*ptr, dpSet, true);

		return;
	}
	else
	{
		Logger::getLogger()->debug("%s:%d :tuple found in cache '%p', '%s': datapoints '%d'",
					__FUNCTION__,
					__LINE__,
					(it->first),
					(it->first)->assetToString().c_str(),
					(it->second).size());

		// record is found in cache , compare the datapoints of the argument ptr to that present in the cache
		// update the cache with datapoints present in argument record but  absent in cache

		std::set<std::string> &cacheRecord = it->second;
		unsigned int sizeOfCacheRecord = cacheRecord.size();

		// store all the datapoints to be updated in string strDatapoints which is sent to management_client
		std::string strDatapoints;
		unsigned int count = 0;
		for (auto itr : cacheRecord)
		{
			strDatapoints.append(itr);
			strDatapoints.append(",");
			count++;
		}

		// check which datapoints are not present in cache record, and need to be updated
		// in cache and db, store them in string strDatapoints, in comma-separated format
		for(auto itr: dpSet)
		{
			if (cacheRecord.find(itr) == cacheRecord.end())
			{
				strDatapoints.append(itr);
				strDatapoints.append(",");
				count++;
			}
		}

		// remove the last comma
		if (strDatapoints[strDatapoints.size()-1] == ',')
		{
			strDatapoints.pop_back();
		}

		if (count <= sizeOfCacheRecord)
		{
			// No need to update as count of cache record is not getting increased
			return;
		}

		// Add current StorageAssetTrackingTuple to the process queue
		addStorageAssetTrackingTuple(*(it->first), dpSet);

		// if update of DB successful , then update the CacheRecord
		for(auto itr: dpSet)
		{
			if (cacheRecord.find(itr) == cacheRecord.end())
			{
				cacheRecord.insert(itr);
			}
		}
	}
}

/**
 * Add asset tracking tuple via microservice management API and in cache
 *
 * @param tuple         New tuple to add  to the queue
 * @param dpSet		Set of datapoints to handle
 * @param addObj	Create a new obj for cache and queue if true.
 * 			Otherwise just add current tuple to processing queue.
 */
void AssetTracker::addStorageAssetTrackingTuple(StorageAssetTrackingTuple& tuple,
						std::set<std::string>& dpSet,
						bool addObj)
{
	// Create a comma separated list of datapoints
	std::string strDatapoints;
	unsigned int count = 0;
	for (auto itr : dpSet)
	{
		strDatapoints.append(itr);
		strDatapoints.append(",");
		count++;
	}
	if (strDatapoints[strDatapoints.size()-1] == ',')
	{
		strDatapoints.pop_back();
	}

	if (addObj)
	{
		// Create new tuple from input one
		StorageAssetTrackingTuple *ptr = new StorageAssetTrackingTuple(tuple);

		// Add new tuple to storage asset cache
		storageAssetTrackerTuplesCache.emplace(ptr, dpSet);

		// Add datapoints and count needed for data insert
		ptr->m_datapoints = strDatapoints;
		ptr->m_maxCount = count;

		// Add new tuple to processing queue
		queue(ptr);
	}
	else
	{
		// Add datapoints and count needed for data insert
		tuple.m_datapoints = strDatapoints;
		tuple.m_maxCount = count;

		// Just add current tuple to processing queue
		queue(&tuple);
	}
}

/**
 * Insert AssetTrackingTuple data via Fledge core API
 * or prepare InsertValues object for direct DB operation
 *
 * @param storage	Boolean for storage being available
 * @param mgtClient	ManagementClient object pointer
 * @param warned	Boolean ireference updated for logging operation
 * @param instanceName	Fledge instance name
 * @return 		InsertValues object
 */
InsertValues AssetTrackingTuple::processData(bool storage,
					ManagementClient *mgtClient,
					bool &warned,
					string &instanceName)
{
	InsertValues iValue;

	// Write the tuple - ideally we would like a bulk update here or to go direct to the
	// database. However we need the Fledge service name  passed in instanceName
	if (!storage)
	{
		// Fall back to using interface to the core
		if (!warned)
		{
			Logger::getLogger()->warn("Asset tracker falling back to core API");
		}
		warned = true;

		mgtClient->addAssetTrackingTuple(m_serviceName,
					m_pluginName,
					m_assetName,
					m_eventName);
	}
	else
	{
		iValue.push_back(InsertValue("asset",   m_assetName));
		iValue.push_back(InsertValue("event",   m_eventName));
		iValue.push_back(InsertValue("service", m_serviceName));
		iValue.push_back(InsertValue("fledge",  instanceName));
		iValue.push_back(InsertValue("plugin",  m_pluginName));
	}

	return iValue;
}

/**
 * Insert StorageAssetTrackingTuple data via Fledge core API
 * or prepare InsertValues object for direct DB operation
 *
 * @param storage	Boolean for storage being available
 * @param mgtClient	ManagementClient object pointer
 * @param warned	Boolean ireference updated for logging operation
 * @param instanceName	Fledge instance name
 * @return 		InsertValues object
 */
InsertValues StorageAssetTrackingTuple::processData(bool storage,
						ManagementClient *mgtClient,
						bool &warned,
						string &instanceName)
{
	InsertValues iValue;

	// Write the tuple - ideally we would like a bulk update here or to go direct to the
	// database. However we need the Fledge service name for that, which is now in
	// the member variable m_fledgeName
	if (!storage)
	{
		// Fall back to using interface to the core
		if (!warned)
		{
			Logger::getLogger()->warn("Storage Asset tracker falling back to core API");
		}
		warned = true;

		// Insert tuple via Fledge core API
		mgtClient->addStorageAssetTrackingTuple(m_serviceName,
							m_pluginName,
							m_assetName,
							m_eventName,
							false,
							m_datapoints,
							m_maxCount);
	}
	else
	{
		iValue.push_back(InsertValue("asset",	m_assetName));
		iValue.push_back(InsertValue("event",	m_eventName));
		iValue.push_back(InsertValue("service",	m_serviceName));
		iValue.push_back(InsertValue("fledge",	instanceName));
		iValue.push_back(InsertValue("plugin",	m_pluginName));

		// prepare JSON datapoints
		string datapoints = "\"";
		for ( int i = 0; i < m_datapoints.size(); ++i)
		{
			if (m_datapoints[i] == ',')
			{
				datapoints.append("\",\"");
			}
			else
			{
				datapoints.append(1,m_datapoints[i]);
			}
		}
		datapoints.append("\"");

		Document doc;
		string jsonData = "{\"count\": " +
				std::to_string(m_maxCount) +
				", \"datapoints\": [" +
				datapoints + "]}";
		doc.Parse(jsonData.c_str());
		iValue.push_back(InsertValue("data", doc));
	}

	return iValue;
}

/**
 * Check if a StorageAssetTrackingTuple is in cache
 *
 * @param tuple	The StorageAssetTrackingTuple to find
 * @return	Pointer to found tuple or NULL
 */
StorageAssetTrackingTuple* AssetTracker::findStorageAssetTrackingCache(StorageAssetTrackingTuple& tuple)
{
	StorageAssetCacheMapItr it = storageAssetTrackerTuplesCache.find(&tuple);

        if (it == storageAssetTrackerTuplesCache.end())
	{
		return NULL;
	}
	else
	{
		return it->first;
	}
}

/**
 * Get stored value in the StorageAssetTrackingTuple cache for the given tuple
 *
 * @param tuple	The StorageAssetTrackingTuple to find
 * @return	Pointer to found std::set<std::string> result or NULL if tuble does not exist
 */
std::set<std::string>* AssetTracker::getStorageAssetTrackingCacheData(StorageAssetTrackingTuple* tuple)
{
	StorageAssetCacheMapItr it = storageAssetTrackerTuplesCache.find(tuple);

        if (it == storageAssetTrackerTuplesCache.end())
	{
		return NULL;
	}
	else
	{
		return &(it->second);
	}
}
