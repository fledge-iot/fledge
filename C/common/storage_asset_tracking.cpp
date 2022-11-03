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
			set<string> setOfDPs = getDataPointsSet(rec->m_datapoints);
			if (setOfDPs.size() == 0)
			{
				Logger::getLogger()->warn("%s:%d Datapoints unavailable for service %s ",  __FUNCTION__, __LINE__, m_service.c_str());
			}
			storageAssetTrackerTuplesCache[rec] = setOfDPs;
		}
		delete (&vec);
	}
	catch (...)
	{
		Logger::getLogger()->error("%s:%d Failed to populate storage asset tracking tuples' cache",  __FUNCTION__, __LINE__);
		return;
	}

	return;
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
			Logger::getLogger()->error("%s:%d, m_mgtClient Ptr is NULL", __FUNCTION__, __LINE__);
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
				Logger::getLogger()->error("%s:%d, serviceName is not an object",  __FUNCTION__, __LINE__);	
				return false;
			}

			if (!serviceName.HasMember("value"))
			{
				Logger::getLogger()->error("%s:%d, serviceName has no member value", __FUNCTION__, __LINE__);
				return false;

			}
			Value& serviceVal = serviceName["value"];
			if ( !serviceVal.IsString())
			{
				Logger::getLogger()->error("%s:%d, serviceVal is not a string",  __FUNCTION__, __LINE__);
				return false;
			}

			m_fledgeService = serviceVal.GetString();    
			Logger::getLogger()->error("%s:%d, m_plugin value = %s", __FUNCTION__, __LINE__, m_fledgeService.c_str());
    			return true;
                }
		  
	} catch (const SimpleWeb::system_error &e) {
		Logger::getLogger()->error("Get service failed %s.", e.what());
                return false;
        }
        return false;
}

/**
 *  Updates datapoints present in the arg dpSet in the cache
 *
 * @param dpSet             set of datapoints string values to be updated in cache
 * @param ptr               StorageAssetTrackingTuple* , as key in cache (map) 
 * Retval void
 */

void StorageAssetTracker::updateCache(std::set<std::string> dpSet, StorageAssetTrackingTuple* ptr)
{
	unsigned int sizeOfInputSet = dpSet.size();
        StorageAssetCacheMapItr it = storageAssetTrackerTuplesCache.find(ptr);

	// search for the record in cache , if not present, simply update cache and return
        if (it == storageAssetTrackerTuplesCache.end())
        {
                Logger::getLogger()->debug("%s:%d :tuple not found in cache ", __FUNCTION__, __LINE__);
		storageAssetTrackerTuplesCache[ptr] = dpSet;
		return;
        }
        else
        {
		// record is found in cache , compare the datapoints of the argument ptr to that present in the cache
		// update the cache with datapoints present in argument record but  absent in cache
		//
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
			strDatapoints.pop_back();

		// Update the DB
		bool rv = m_mgtClient->addStorageAssetTrackingTuple(ptr->getServiceName(), ptr->getPluginName(), ptr->getAssetName(), ptr->getEventName(), false, strDatapoints, count);
		if(rv)
		{
			// if update of DB successful , then update the CacheRecord
			for(auto itr: dpSet)
                	{
                        	if (cacheRecord.find(itr) == cacheRecord.end())
                        	{
                                	cacheRecord.insert(itr);
                        	}
                	}
		}
		else
		{
			// Log error if Update DB unsuccessful
			 Logger::getLogger()->error("%s:%d: Failed to insert storage asset tracking tuple into DB: '%s'", __FUNCTION__, __LINE__, (ptr->getAssetName()).c_str());

		}
	}
}

//This function takes a string of datapoints in comma-separated format and returns 
//set of string datapoint values 
std::set<std::string> StorageAssetTracker::getDataPointsSet(std::string strDatapoints)
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


/** This function takes a StorageAssetTrackingTuple pointer and searches for
 *  it in cache, if found then returns its Deprecated status
 *
 * @param ptr           StorageAssetTrackingTuple* , as key in cache (map)
 * Retval bool 		Deprecation status 
 */


bool StorageAssetTracker::getDeprecated(StorageAssetTrackingTuple* ptr)
{
	StorageAssetCacheMapItr it = storageAssetTrackerTuplesCache.find(ptr);

        if (it == storageAssetTrackerTuplesCache.end())
        {
                Logger::getLogger()->debug("%s:%d :tuple not found in cache ", __FUNCTION__, __LINE__);
		return true;
        }
        else
        {
		return (it->first)->isDeprecated();
	}

	return false;
}
