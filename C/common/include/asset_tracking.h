#ifndef _ASSET_TRACKING_H
#define _ASSET_TRACKING_H
/*
 * Fledge asset tracking related
 *
 * Copyright (c) 2018 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Amandeep Singh Arora, Massimiliano Pinto
 */
#include <logger.h>
#include <vector>
#include <set>
#include <sstream>
#include <unordered_set>
#include <management_client.h>
#include <queue>
#include <thread>
#include <mutex>
#include <condition_variable>
#include <storage_client.h>

#define MIN_ASSET_TRACKER_UPDATE	500 // The minimum interval for asset tracker updates

/**
 * Tracking abstract base class to be passed in the process data queue
 */
class TrackingTuple {
public:
	TrackingTuple() {};
	virtual ~TrackingTuple() = default;
	virtual InsertValues processData(bool storage_connected,
					ManagementClient *mgtClient,
					bool &warned,
					std::string &instanceName) = 0;
	virtual std::string assetToString() = 0;
};


/**
 * The AssetTrackingTuple class is used to represent an asset
 * tracking tuple. Hash function and '==' operator are defined for
 * this class and pointer to this class that would be required
 * to create an unordered_set of this class.
 */
class AssetTrackingTuple : public TrackingTuple {

public:
	std::string	assetToString()
	{
		std::ostringstream o;
		o << "service:" << m_serviceName <<
			", plugin:" << m_pluginName <<
			", asset:" << m_assetName <<
			", event:" << m_eventName <<
			", deprecated:" << m_deprecated;
		return o.str();
	}

	inline bool operator==(const AssetTrackingTuple& x) const
	{
		return ( x.m_serviceName==m_serviceName &&
			x.m_pluginName==m_pluginName &&
			x.m_assetName==m_assetName &&
			x.m_eventName==m_eventName);
	};

	AssetTrackingTuple(const std::string& service,
			const std::string& plugin, 
			const std::string& asset,
			const std::string& event,
			const bool& deprecated = false) :
			m_serviceName(service),
			m_pluginName(plugin), 
			m_assetName(asset),
			m_eventName(event),
			m_deprecated(deprecated) {}

	std::string	&getAssetName() { return m_assetName; };
	std::string     getPluginName() { return m_pluginName;}
	std::string     getEventName()  { return m_eventName;}
	std::string	getServiceName() { return m_serviceName;}
	bool		isDeprecated() { return m_deprecated; };
	void		unDeprecate() { m_deprecated = false; };

	InsertValues	processData(bool storage_connected,
				ManagementClient *mgtClient,
				bool &warned,
				std::string &instanceName);

public:
	std::string 	m_serviceName;
	std::string 	m_pluginName;
	std::string 	m_assetName;
	std::string 	m_eventName;

private:
	bool		m_deprecated;
};

struct AssetTrackingTuplePtrEqual {
    bool operator()(AssetTrackingTuple const* a, AssetTrackingTuple const* b) const {
        return *a == *b;
    }
};

namespace std
{
    template <>
    struct hash<AssetTrackingTuple>
    {
        size_t operator()(const AssetTrackingTuple& t) const
        {
            return (std::hash<std::string>()(t.m_serviceName + t.m_pluginName + t.m_assetName + t.m_eventName));
        }
    };

	template <>
    struct hash<AssetTrackingTuple*>
    {
        size_t operator()(AssetTrackingTuple* t) const
        {
            return (std::hash<std::string>()(t->m_serviceName + t->m_pluginName + t->m_assetName + t->m_eventName));
        }
    };
}

class StorageAssetTrackingTuple : public TrackingTuple {
public:
	StorageAssetTrackingTuple(const std::string& service,
				const std::string& plugin,
				const std::string& asset,
				const std::string& event,
				const bool& deprecated = false,
				const std::string& datapoints = "",
				unsigned int c = 0) : m_datapoints(datapoints),
					m_maxCount(c),
					m_serviceName(service),
					m_pluginName(plugin),
					m_assetName(asset),
					m_eventName(event),
					m_deprecated(deprecated)
				{};

	inline bool operator==(const StorageAssetTrackingTuple& x) const
	{
		return ( x.m_serviceName==m_serviceName &&
			x.m_pluginName==m_pluginName &&
			x.m_assetName==m_assetName &&
			x.m_eventName==m_eventName);
	};
	std::string	assetToString()
	{
		std::ostringstream o;
		o << "service:" << m_serviceName <<
			", plugin:" << m_pluginName <<
			", asset:" << m_assetName <<
			", event:" << m_eventName <<
			", deprecated:" << m_deprecated <<
			", m_datapoints:" << m_datapoints <<
			", m_maxCount:" << m_maxCount;
		return o.str();
	};

	bool		isDeprecated() { return m_deprecated; };

	unsigned int	getMaxCount() { return m_maxCount; }
	std::string	getDataPoints() { return m_datapoints; }
	void		unDeprecate() { m_deprecated = false; };
	void		setDeprecate() { m_deprecated = true; };

	InsertValues	processData(bool storage,
				ManagementClient *mgtClient,
				bool &warned,
				std::string &instanceName);

public:
	std::string	m_datapoints;
	unsigned int	m_maxCount;
	std::string	m_serviceName;
	std::string	m_pluginName;
	std::string	m_assetName;
	std::string	m_eventName;

private:
	bool		m_deprecated;
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
			return (std::hash<std::string>()(t.m_serviceName +
							t.m_pluginName +
							t.m_assetName +
							t.m_eventName));
		}
	};

	template <>
	struct hash<StorageAssetTrackingTuple*>
	{
		size_t operator()(StorageAssetTrackingTuple* t) const
		{
			return (std::hash<std::string>()(t->m_serviceName +
							t->m_pluginName +
							t->m_assetName +
							t->m_eventName));
		}
	};
}

typedef std::unordered_map<StorageAssetTrackingTuple*,
			std::set<std::string>,
			std::hash<StorageAssetTrackingTuple*>,
			StorageAssetTrackingTuplePtrEqual> StorageAssetCacheMap;
typedef std::unordered_map<StorageAssetTrackingTuple*,
			std::set<std::string>,
			std::hash<StorageAssetTrackingTuple*>,
			StorageAssetTrackingTuplePtrEqual>::iterator StorageAssetCacheMapItr;

class ManagementClient;

/**
 * The AssetTracker class provides the asset tracking functionality.
 * There are methods to populate asset tracking cache from asset_tracker DB table,
 * and methods to check/add asset tracking tuples to DB and to cache
 */
class AssetTracker {

public:
	AssetTracker(ManagementClient *mgtClient, std::string service);
	~AssetTracker();
	static AssetTracker *getAssetTracker();
	void	populateAssetTrackingCache(std::string plugin, std::string event);
	void	populateStorageAssetTrackingCache();
	bool	checkAssetTrackingCache(AssetTrackingTuple& tuple);
	AssetTrackingTuple*
		findAssetTrackingCache(AssetTrackingTuple& tuple);
	void	addAssetTrackingTuple(AssetTrackingTuple& tuple);
	void	addAssetTrackingTuple(std::string plugin, std::string asset, std::string event);
	void	addStorageAssetTrackingTuple(StorageAssetTrackingTuple& tuple,
					std::set<std::string>& dpSet,
					bool addObj = false);
	StorageAssetTrackingTuple*
		findStorageAssetTrackingCache(StorageAssetTrackingTuple& tuple);
	std::string
		getIngestService(const std::string& asset)
		{
			return getService("Ingest", asset);
		};
	std::string
		getEgressService(const std::string& asset)
		{
			return getService("Egress", asset);
		};
	void	workerThread();

	bool	getDeprecated(StorageAssetTrackingTuple* ptr);
	void	updateCache(std::set<std::string> dpSet, StorageAssetTrackingTuple* ptr);
	std::set<std::string>
		*getStorageAssetTrackingCacheData(StorageAssetTrackingTuple* tuple);
	bool	tune(unsigned long updateInterval);

private:
	std::string
		getService(const std::string& event, const std::string& asset);
	void	queue(TrackingTuple *tuple);
	void	processQueue();
	std::set<std::string>
		getDataPointsSet(std::string strDatapoints);
	bool	getFledgeConfigInfo();

private:
	static AssetTracker			*instance;
	ManagementClient			*m_mgtClient;
	std::string				m_service;
	std::unordered_set<AssetTrackingTuple*, std::hash<AssetTrackingTuple*>, AssetTrackingTuplePtrEqual>
						assetTrackerTuplesCache;
	std::queue<TrackingTuple *>		m_pending;	// Tuples that are not yet written to the storage
	std::thread				*m_thread;
	bool					m_shutdown;
	std::condition_variable			m_cv;
	std::mutex				m_mutex;
	std::string				m_fledgeName;
	StorageClient				*m_storageClient;
	StorageAssetCacheMap			storageAssetTrackerTuplesCache;
	unsigned int				m_updateInterval;
};

/**
 * A class to hold a set of asset tracking tuples that allows
 * lookup by name.
 */
class AssetTrackingTable {
	public:
		AssetTrackingTable();
		~AssetTrackingTable();
		void			add(AssetTrackingTuple *tuple);
		void			remove(const std::string& name);
		AssetTrackingTuple	*find(const std::string& name);
	private:
		std::map<std::string, AssetTrackingTuple *>
				m_tuples;
};

#endif
