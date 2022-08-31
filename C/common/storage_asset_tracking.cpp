/*
 * Fledge asset tracking related
 *
 t* Copyright (c) 2019 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Amandeep Singh Arora
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
	Logger::getLogger()->error("%s:%s StorageAssetTracker constructor called ",__FILE__, __FUNCTION__);
	instance = this;
}

/**
 * Fetch all asset tracking tuples from DB and populate local cache
 *
 * Return the vector of deprecated asset names
 *
 * @param plugin  	Plugin name
 * @param event  	Event name
 */
void StorageAssetTracker::populateStorageAssetTrackingCache()
{
	Logger::getLogger()->error("%s:%s populateStorageAssetTrackingCache start", __FILE__, __FUNCTION__);
	try {
		std::vector<StorageAssetTrackingTuple*>& vec = m_mgtClient->getStorageAssetTrackingTuples(m_service);
		 Logger::getLogger()->error("%s:%s  m_mgtClient->getStorageAssetTrackingTuples returned vec of size %d", __FILE__, __FUNCTION__, vec.size());
		for (StorageAssetTrackingTuple* & rec : vec)
		{
			storageAssetTrackerTuplesCache.insert(rec);

			Logger::getLogger()->error("Added asset tracker tuple to cache: '%s'",
					rec->assetToString().c_str());
		}
		delete (&vec);
	}
	catch (...)
	{
		Logger::getLogger()->error("Failed to populate asset tracking tuples' cache");
		return;
	}

	Logger::getLogger()->error("%s:%s populateStorageAssetTrackingCache end", __FILE__, __FUNCTION__);

	return;
}

/**
 * Check local cache for a given asset tracking tuple
 *
 * @param tuple		Tuple to find in cache
 * @return		Returns whether tuple is present in cache
 */
bool StorageAssetTracker::checkStorageAssetTrackingCache(StorageAssetTrackingTuple& tuple)	
{

	Logger::getLogger()->error("%s:%s :checkStorageAssetTrackingCache start ", __FILE__, __FUNCTION__);
	StorageAssetTrackingTuple *ptr = &tuple;
	std::unordered_set<StorageAssetTrackingTuple*>::const_iterator it = storageAssetTrackerTuplesCache.find(ptr);

        Logger::getLogger()->error("%s:%s :storageAssetTrackerTuplesCache 2 ", __FILE__, __FUNCTION__);

	if (it == storageAssetTrackerTuplesCache.end())
	{
		Logger::getLogger()->error("%s:%s :checkStorageAssetTrackingCache tuple not in cache", __FILE__, __LINE__);
		return false;
	}
	else
	{
		if ((*it)->m_maxCount >= ptr->m_maxCount)
		{
			Logger::getLogger()->error("%s:%s :checkStorageAssetTrackingCache  tuple in database count > = tuple in arg count, returnin true ", __FILE__, __LINE__);
			return true;
		}
		else
		{
			Logger::getLogger()->error("%s:%s :checkStorageAssetTrackingCache  tuple in database count < tuple in arg count, returning false", __FILE__, __LINE__);

			return false;
		}
	}
	 Logger::getLogger()->error("%s:%s :storageAssetTrackerTuplesCache  end ", __FILE__, __FUNCTION__);

}

StorageAssetTrackingTuple* StorageAssetTracker::findStorageAssetTrackingCache(StorageAssetTrackingTuple& tuple)	
{
	StorageAssetTrackingTuple *ptr = &tuple;
	std::unordered_set<StorageAssetTrackingTuple*>::const_iterator it = storageAssetTrackerTuplesCache.find(ptr);
	if (it == storageAssetTrackerTuplesCache.end())
	{
	        Logger::getLogger()->error("%s:%d :findStorageAssetTrackingCache tuple not found in cache ", __FILE__, __LINE__);
		return NULL;
	}
	else
	{
		Logger::getLogger()->error("%s:%d :findStorageAssetTrackingCache tuple found in cache ", __FILE__, __LINE__);
		return *it;
	}
}

/**
 * Add asset tracking tuple via microservice management API and in cache
 *
 * @param tuple		New tuple to add in DB and in cache
 */
void StorageAssetTracker::addStorageAssetTrackingTuple(StorageAssetTrackingTuple& tuple)
{
	Logger::getLogger()->error("%s:%d, addStorageAssetTrackingTuple start" ,__FILE__, __LINE__);
	std::unordered_set<StorageAssetTrackingTuple*>::const_iterator it = storageAssetTrackerTuplesCache.find(&tuple);
	if (it == storageAssetTrackerTuplesCache.end())
	{
		Logger::getLogger()->error("%s:%d, addStorageAssetTrackingTuple tuple not found in cache, insert in DB",  __FILE__, __LINE__);
		bool rv = m_mgtClient->addAssetTrackingTuple(tuple.m_serviceName, tuple.m_pluginName, tuple.m_assetName, tuple.m_eventName, tuple.m_datapoints, tuple.m_maxCount);

		if (rv) // insert into cache only if DB operation succeeded
		{
			StorageAssetTrackingTuple *ptr = new StorageAssetTrackingTuple(tuple);
			storageAssetTrackerTuplesCache.insert(ptr);
			Logger::getLogger()->info("addStorgeAssetTrackingTuple(): Added tuple to cache: %s, insert in db successful ", tuple.assetToString().c_str());
		}
		else
			Logger::getLogger()->error("addStorageAssetTrackingTuple(): Failed to insert asset tracking tuple into DB: '%s'", tuple.assetToString().c_str());
	}
	Logger::getLogger()->error("%s:%d, addStorageAssetTrackingTuple end", __FILE__, __LINE__);
}

/**
 * Add asset tracking tuple via microservice management API and in cache
 *
 * @param plugin	Plugin name
 * @param asset		Asset name
 * @param event		Event name
 */
/*void StorageAssetTracker::addStorageAssetTrackingTuple(std::string asset, std::string datapoints, int maxCount)
{

	Logger::getLogger()->error("%s:%s calling addStorageAssetTrackingTuple(tuple)", __FILE__, __FUNCTION__);
	
	StorageAssetTrackingTuple tuple(m_service, m_plugin, asset, m_event, false, datapoints, maxCount);
	addStorageAssetTrackingTuple(tuple);
}
*/
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


