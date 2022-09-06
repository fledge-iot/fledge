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

	Logger::getLogger()->error("%s:%s +++++++++++++++++populateStorageAssetTrackingCache start+++++++++++++++", __FILE__, __FUNCTION__);
	try {
		std::vector<StorageAssetTrackingTuple*>& vec = m_mgtClient->getStorageAssetTrackingTuples(m_service);
		 Logger::getLogger()->error("%s:%s  m_mgtClient->getStorageAssetTrackingTuples returned vec of size %d", __FILE__, __FUNCTION__, vec.size());
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

			Logger::getLogger()->error("%s:%s Added storage asset tracker tuple to cache: '%s'", __FILE__, __FUNCTION__,
					rec->assetToString().c_str());
		}
		delete (&vec);
	}
	catch (...)
	{
		Logger::getLogger()->error("%s:%s Failed to populate storage asset tracking tuples' cache", __FILE__, __FUNCTION__);
		return;
	}

	Logger::getLogger()->error("%s:%s size of multiset %d", __FILE__, __FUNCTION__,
                                        storageAssetTrackerTuplesCache.size());

	return;
}


StorageAssetTrackingTuple* StorageAssetTracker::findStorageAssetTrackingCache(StorageAssetTrackingTuple& tuple)	
{
	StorageAssetTrackingTuple *ptr = &tuple;
	std::unordered_multiset<StorageAssetTrackingTuple*>::const_iterator it = storageAssetTrackerTuplesCache.find(ptr);

	Logger::getLogger()->error("%s:%s :findStorageAssetTrackingCache : storageAssetTrackerTuplesCache.size()=%d ,tupleto find dp = %s", __FILE__, __FUNCTION__, storageAssetTrackerTuplesCache.size(), ptr->m_datapoints.c_str());

	Logger::getLogger()->error("%s:%s : Printing cache , size being %d", __FILE__, __FUNCTION__, storageAssetTrackerTuplesCache.size());

	for (auto tuple : storageAssetTrackerTuplesCache)
	{
		Logger::getLogger()->error("%s:%s:%s:%s:%s:%d", tuple->m_serviceName.c_str(), tuple->m_pluginName.c_str(), tuple->m_assetName.c_str(), tuple->m_eventName.c_str(), tuple->m_datapoints.c_str(), tuple->m_maxCount);
	}

	if (it == storageAssetTrackerTuplesCache.end())
	{
	        Logger::getLogger()->error("%s:%s :findStorageAssetTrackingCache tuple not found in cache ", __FILE__, __FUNCTION__);
		return NULL;
	}
	else
	{
		Logger::getLogger()->error("%s:%s :findStorageAssetTrackingCache tuple found in cache dp = %s", __FILE__, __FUNCTION__, (*it)->m_datapoints.c_str());

		Logger::getLogger()->error("%s:%s :findStorageAssetTrackingCache tuple found in cache , arg dp = %s", __FILE__, __FUNCTION__, (ptr)->m_datapoints.c_str());


		   // tuple present and count value < count of reading, update cache
                if ((*it)->m_maxCount < ptr->m_maxCount)
                {
			// record to be updated in tuple, delete old one 
	                storageAssetTrackerTuplesCache.erase(it);

			Logger::getLogger()->error("%s:%d:%s tuple present and count value < count of reading, update cache, erased dp%s ",  __FILE__,__LINE__, __FUNCTION__, (*it)->m_datapoints.c_str());
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
				Logger::getLogger()->error("%s:%d:%s tuple present and case where counts are same but datapoints are different, update cache ",  __FILE__,__LINE__, __FUNCTION__);

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
 * Add asset tracking tuple via microservice management API and in cache
 *
 * @param tuple		New tuple to add in DB and in cache
 */
void StorageAssetTracker::addStorageAssetTrackingTuple(StorageAssetTrackingTuple& tuple)
{
	std::unordered_multiset<StorageAssetTrackingTuple*>::const_iterator it = storageAssetTrackerTuplesCache.find(&tuple);

	Logger::getLogger()->error("%s:%d, addStorageAssetTrackingTuple: tuple to add : service:%s, plugin:%s, asset:%s, event:%s, datapoints:%s, count:%d ",__FILE__, __LINE__,  tuple.m_serviceName.c_str(), tuple.m_pluginName.c_str(), tuple.m_assetName.c_str(), tuple.m_eventName.c_str(), tuple.m_datapoints.c_str(), tuple.m_maxCount);
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

	Logger::getLogger()->error("%s:%s temp1 = %s , temp1.size = %d , temp2 = %s , temp2 size %d , return value %d", __FILE__, __FUNCTION__, temp1.c_str(), temp1.size(), temp2.c_str(), temp2.size(), temp1.compare(temp2)); 
	return temp1.compare(temp2);
}


