#ifndef _STORAGE_ASSET_TRACKING_H
#define _STORAGE_ASSET_TRACKING_H
/*
 * Fledge storage asset tracking related
 *
 * Copyright (c) 2022 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Ashwini Sinha
 */
#include <logger.h>
#include <vector>
#include <sstream>
#include <unordered_set>
#include <asset_tracking.h>
#include <management_client.h>
#include <set>


/**
 * The StorageAssetTrackingTuple class is used to represent ai storage asset
 * tracking tuple. Hash function and '==' operator are defined for
 * this class and pointer to this class that would be required
 * to create an unordered_set of this class.
 */

class StorageAssetTrackingTuple : public AssetTrackingTuple {

public:
	std::string	m_datapoints;
	unsigned int	m_maxCount;

	std::string assetToString()
	{
		std::ostringstream o;
		o << AssetTrackingTuple::assetToString() << ", m_datapoints:" << m_datapoints << ", m_maxCount:" << m_maxCount;
		return o.str();
	}

	unsigned int getMaxCount() { return m_maxCount; }
	std::string getDataPoints() { return m_datapoints; }

	StorageAssetTrackingTuple(const std::string& service,
			const std::string& plugin, 
			const std::string& asset,
			const std::string& event,
			const bool& deprecated = false,
			const std::string& datapoints = "",
			unsigned int c = 0) :
			AssetTrackingTuple(service, plugin, asset, event, deprecated), m_datapoints(datapoints), m_maxCount(c)
	{}

private:
};

struct StorageAssetTrackingTuplePtrEqual {
    bool operator()(StorageAssetTrackingTuple const* a, StorageAssetTrackingTuple const* b) const {
        return *a == *b;
    }
};

namespace std
{
    template <>
    struct hash<StorageAssetTrackingTuple>
    {
        size_t operator()(const StorageAssetTrackingTuple& t) const
        {
            return (std::hash<std::string>()(t.m_serviceName + t.m_pluginName + t.m_assetName + t.m_eventName));
        }
    };

	template <>
    struct hash<StorageAssetTrackingTuple*>
    {
        size_t operator()(StorageAssetTrackingTuple* t) const
        {
            return (std::hash<std::string>()(t->m_serviceName + t->m_pluginName + t->m_assetName + t->m_eventName));
        }
    };
}

class ManagementClient;

typedef std::unordered_multiset<StorageAssetTrackingTuple*, std::hash<StorageAssetTrackingTuple*>, StorageAssetTrackingTuplePtrEqual> StorageAssetCacheSet;

typedef std::unordered_multiset<StorageAssetTrackingTuple*, std::hash<StorageAssetTrackingTuple*>, StorageAssetTrackingTuplePtrEqual>::iterator StorageAssetCacheSetItr;

struct StorageAssetCacheSetItrCmp{

	bool operator ()(StorageAssetCacheSetItr x, StorageAssetCacheSetItr y)
	{
		return x != y;
	}

};
/**
 * The StorageAssetTracker class provides the asset tracking functionality.
 * There are methods to populate asset tracking cache from asset_tracker DB table,
 * and methods to check/add asset tracking tuples to DB and to cache
 */
class StorageAssetTracker {

public:
	StorageAssetTracker(ManagementClient *mgtClient, std::string m_service);
	~StorageAssetTracker() {}
	void	populateStorageAssetTrackingCache();
	StorageAssetTrackingTuple*
		findStorageAssetTrackingCache(StorageAssetTrackingTuple& tuple);
	void	addStorageAssetTrackingTuple(StorageAssetTrackingTuple& tuple);
	bool 	getFledgeConfigInfo();
	static  StorageAssetTracker *getStorageAssetTracker();
	static	void releaseStorageAssetTracker();
	int 	compareDatapoints(const std::string& dp1, const std::string& dp2);

private:
	static StorageAssetTracker	*instance;
	ManagementClient		*m_mgtClient;
	std::string                     m_fledgeService;
	std::string			m_service;
	std::string			m_event;

	StorageAssetCacheSet storageAssetTrackerTuplesCache;
};

#endif
