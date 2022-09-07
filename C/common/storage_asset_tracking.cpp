/*
 * Fledge Storage asset tracking related
 *
 * Copyright (c) 2022 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Ashwini Sinha
 */

#include <logger.h>
#include <storage_asset_tracking.h>

using namespace std;

StorageAssetTracker *StorageAssetTracker::instance = 0;

/**
 * Get asset tracker singleton instance for the current south service
 *
 * @return	Singleton asset tracker instance
 */
StorageAssetTracker *StorageAssetTracker::getStorageAssetTracker()
{
	return instance;
}

/**
 * Release the storage asset tracker singleton instance 
 *
 * @return      void 
 */

void StorageAssetTracker::releaseStorageAssetTracker()
{
        if (instance)
                delete instance;
       	instance = nullptr; 
}


/**
 * AssetTracker class constructor
 *
 * @param mgtClient		Management client object for this south service
 * @param service  		Service name
 */
StorageAssetTracker::StorageAssetTracker(ManagementClient *mgtClient, std::string service) 
	: m_mgtClient(mgtClient), m_service(service), m_event("store")
{
	instance = this;
}

/**
 * Fetch all storage asset tracking tuples from DB and populate local cache
 *
 * Return the vector of deprecated asset names
 *
 */
void StorageAssetTracker::populateStorageAssetTrackingCache()
{

	try {
		std::vector<StorageAssetTrackingTuple*>& vec = m_mgtClient->getStorageAssetTrackingTuples(m_service);
		for (StorageAssetTrackingTuple* & rec : vec)
		{
			auto it = storageAssetTrackerTuplesCache.find(rec);
			if (it == storageAssetTrackerTuplesCache.end())
			{
				// tuple not found in cache , so add it
				storageAssetTrackerTuplesCache.insert(rec);
			}
			else
			{
				// tuple present and count value < count of reading, update cache
				if ((*it)->m_maxCount < rec->m_maxCount)
				{
					storageAssetTrackerTuplesCache.erase(it);
					storageAssetTrackerTuplesCache.insert(rec);
				}
				else if ((*it)->m_maxCount == rec->m_maxCount)
				{
					// case where counts are same but datapoints are different
					// "a", "b", "c" and "a", "b", "foo"
					// keep both the records
					if ((*it)->m_datapoints.compare(rec->m_datapoints))
					{
						storageAssetTrackerTuplesCache.insert(rec);
					}
				}
			}

			Logger::getLogger()->debug("%s:%s Added storage asset tracker tuple to cache: '%s'", __FILE__, __FUNCTION__,
					rec->assetToString().c_str());
		}
		delete (&vec);
	}
	catch (...)
	{
		Logger::getLogger()->error("%s:%s Failed to populate storage asset tracking tuples' cache", __FILE__, __FUNCTION__);
		return;
	}


	return;
}

/**
 * Find whether the Storage asset tracking tuple exists in the cache or not
 *
 * Return the pointer to the tuple 
 *
 * @param tuple        StorageAssetTrackingTuple Type
 * @return	       A pointer to StorageAssetTrackingTuple in cache or null
 */


StorageAssetTrackingTuple* StorageAssetTracker::findStorageAssetTrackingCache(StorageAssetTrackingTuple& tuple)	
{
	StorageAssetTrackingTuple *ptr = &tuple;
	std::unordered_multiset<StorageAssetTrackingTuple*>::const_iterator it = storageAssetTrackerTuplesCache.find(ptr);

	if (it == storageAssetTrackerTuplesCache.end())
	{
	        Logger::getLogger()->debug("%s:%s :findStorageAssetTrackingCache tuple not found in cache ", __FILE__, __FUNCTION__);
		return NULL;
	}
	else
	{

		   // tuple present and count value < count of reading, update cache
                if ((*it)->m_maxCount < ptr->m_maxCount)
                {
			// record to be updated in tuple, delete old one 
			Logger::getLogger()->debug("%s:%d:%s tuple present and count value < count of reading, update cache, erased dp%s ",  __FILE__,__LINE__, __FUNCTION__, (*it)->m_datapoints.c_str());

	                storageAssetTrackerTuplesCache.erase(it);
			return NULL;
                }
                else if ((*it)->m_maxCount == ptr->m_maxCount)
                {
                // case where counts are same but datapoints are different
                // "a", "b", "c" and "a", "b", "foo"
                // keep both the records
        	        if (compareDatapoints(ptr->m_datapoints,(*it)->m_datapoints))
               		{
				//  record to be addded 
				Logger::getLogger()->debug("%s:%d:%s tuple present and case where counts are same but datapoints are different, update cache ",  __FILE__,__LINE__, __FUNCTION__);

				return NULL;
                	}
			else
				return *it;
                 }

		// dont need updation , return pointer to tuple in cache
		return *it;
	}
}

/**
 * Add storage asset tracking tuple via microservice management API and in cache
 *
 * @param tuple		New tuple to add in DB and in cache
 */
void StorageAssetTracker::addStorageAssetTrackingTuple(StorageAssetTrackingTuple& tuple)
{
	std::unordered_multiset<StorageAssetTrackingTuple*>::const_iterator it = storageAssetTrackerTuplesCache.find(&tuple);

	bool rv = m_mgtClient->addStorageAssetTrackingTuple(tuple.m_serviceName, tuple.m_pluginName, tuple.m_assetName, tuple.m_eventName, false, tuple.m_datapoints, tuple.m_maxCount);

	if (rv) // insert into cache only if DB operation succeeded
	{
		StorageAssetTrackingTuple *ptr = new StorageAssetTrackingTuple(tuple);
		storageAssetTrackerTuplesCache.insert(ptr);
		Logger::getLogger()->info("%s:%d:%s: Added tuple to cache: %s, insert in db successful ", __FILE__, __LINE__, __FUNCTION__, tuple.assetToString().c_str());
	}
	else
		Logger::getLogger()->error("%s:%d:%s Failed to insert storage asset tracking tuple into DB: '%s'", __FILE__, __LINE__,__FUNCTION__, tuple.assetToString().c_str());
}

/**
 * Return Plugin Information in the Fledge configuration
 *
 * @return bool	True if the plugin info could be obtained
 */
bool StorageAssetTracker::getFledgeConfigInfo()
{
	Logger::getLogger()->error("StorageAssetTracker::getPluginInfo start"); 
        try {
                string url = "/fledge/category/service";
		if (!m_mgtClient)
		{
			Logger::getLogger()->error("%s:%s, m_mgtClient Ptr is NULL", __FILE__, __FUNCTION__);
			return false;
		}

		auto res = m_mgtClient->getHttpClient()->request("GET", url.c_str());
                Document doc;
                string response = res->content.string();
                doc.Parse(response.c_str());
                if (doc.HasParseError())
                {
                        bool httpError = (isdigit(response[0]) && isdigit(response[1]) && isdigit(response[2]) && response[3]==':');
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
				Logger::getLogger()->error("%s:%s, serviceName is not an object", __FILE__, __FUNCTION__);	
				return false;
			}

			if (!serviceName.HasMember("value"))
			{
				Logger::getLogger()->error("%s:%s, serviceName has no member value", __FILE__, __FUNCTION__);
				return false;

			}
			Value& serviceVal = serviceName["value"];
			if ( !serviceVal.IsString())
			{
				Logger::getLogger()->error("%s:%s, serviceVal is not a string", __FILE__, __FUNCTION__);
				return false;
			}

			m_fledgeService = serviceVal.GetString();    
			Logger::getLogger()->error("%s:%s, m_plugin value = %s",__FILE__, __FUNCTION__, m_fledgeService.c_str());
    			return true;
                }
		  
	} catch (const SimpleWeb::system_error &e) {
		Logger::getLogger()->error("Get service failed %s.", e.what());
                return false;
        }
        return false;
}


/**
 * Compare the Datapoints in StorageAssetTracker, they can be '"' enclosed
 *
 * @return int  result of comparison of datapoints strings , 0 when equal
 */
int StorageAssetTracker::compareDatapoints(const std::string& dp1, const std::string& dp2)
{
	std::string temp1, temp2;
	for( int i = 0; i < dp1.size() ; ++i)
	{
		if (dp1[i] != '"')
			temp1.push_back(dp1[i]);
	}

	for( int i = 0; i < dp2.size() ; ++i)
        {
                if (dp2[i] != '"')
                        temp2.push_back(dp2[i]);
        }

	return temp1.compare(temp2);
}


