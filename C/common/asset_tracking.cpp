/*
 * FogLAMP asset tracking related
 *
 * Copyright (c) 2019 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Amandeep Singh Arora
 */

#include <logger.h>
#include <asset_tracking.h>

using namespace std;


AssetTracker *AssetTracker::instance = 0;

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
}

/**
 * Fetch all asset tracking tuples from DB and populate local cache
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
			//Logger::getLogger()->info("Added asset tracker tuple to cache: '%s'", rec->assetToString().c_str());
		}
		delete (&vec);
	}
	catch (...)
	{
		Logger::getLogger()->error("Failed to populate asset tracking tuples' cache");
		return;
	}
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
 * Add asset tracking tuple via microservice management API and in cache
 *
 * @param tuple		New tuple to add in DB and in cache
 */
void AssetTracker::addAssetTrackingTuple(AssetTrackingTuple& tuple)
{
	std::unordered_set<AssetTrackingTuple*>::const_iterator it = assetTrackerTuplesCache.find(&tuple);
	if (it == assetTrackerTuplesCache.end())
	{
		bool rv = m_mgtClient->addAssetTrackingTuple(tuple.m_serviceName, tuple.m_pluginName, tuple.m_assetName, tuple.m_eventName);
		if (rv) // insert into cache only if DB operation succeeded
		{
			AssetTrackingTuple *ptr = new AssetTrackingTuple(tuple);
			assetTrackerTuplesCache.insert(ptr);
			Logger::getLogger()->info("addAssetTrackingTuple(): Added tuple to cache: '%s'", tuple.assetToString().c_str());
		}
		else
			Logger::getLogger()->error("addAssetTrackingTuple(): Failed to insert asset tracking tuple into DB: '%s'", tuple.assetToString().c_str());
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
		plugin.erase(plugin.begin(), plugin.begin() + m_service.length() + 1);
	}
	
	AssetTrackingTuple tuple(m_service, plugin, asset, event);
	addAssetTrackingTuple(tuple);
}

