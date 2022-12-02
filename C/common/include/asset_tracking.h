#ifndef _ASSET_TRACKING_H
#define _ASSET_TRACKING_H
/*
 * Fledge asset tracking related
 *
 * Copyright (c) 2018 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Amandeep Singh Arora
 */
#include <logger.h>
#include <vector>
#include <sstream>
#include <unordered_set>
#include <management_client.h>

/**
 * The AssetTrackingTuple class is used to represent an asset
 * tracking tuple. Hash function and '==' operator are defined for
 * this class and pointer to this class that would be required
 * to create an unordered_set of this class.
 */
class AssetTrackingTuple {

public:
	std::string 		m_serviceName;
	std::string 		m_pluginName;
	std::string 		m_assetName;
	std::string 		m_eventName;

	std::string assetToString()
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
	}

	AssetTrackingTuple(const std::string& service,
			const std::string& plugin, 
			const std::string& asset,
			const std::string& event,
			const bool& deprecated = false) :
			m_serviceName(service),
			m_pluginName(plugin), 
			m_assetName(asset),
			m_eventName(event),
			m_deprecated(deprecated)
	{}

	std::string&	getAssetName() { return m_assetName; };
	std::string     getPluginName() { return m_pluginName;}
	std::string     getEventName()  { return m_eventName;}
	std::string	getServiceName() { return m_serviceName;}
	bool		isDeprecated() { return m_deprecated; };
	void		unDeprecate() { m_deprecated = false; };

private:
	bool			m_deprecated;
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

class ManagementClient;

/**
 * The AssetTracker class provides the asset tracking functionality.
 * There are methods to populate asset tracking cache from asset_tracker DB table,
 * and methods to check/add asset tracking tuples to DB and to cache
 */
class AssetTracker {

public:
	AssetTracker(ManagementClient *mgtClient, std::string service);
	~AssetTracker() {}
	static AssetTracker *getAssetTracker();
	void	populateAssetTrackingCache(std::string plugin, std::string event);
	bool	checkAssetTrackingCache(AssetTrackingTuple& tuple);
	AssetTrackingTuple*
		findAssetTrackingCache(AssetTrackingTuple& tuple);
	void	addAssetTrackingTuple(AssetTrackingTuple& tuple);
	void	addAssetTrackingTuple(std::string plugin, std::string asset, std::string event);
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

private:
	std::string
		getService(const std::string& event, const std::string& asset);

private:
	static AssetTracker	*instance;
	ManagementClient	*m_mgtClient;
	std::string		m_service;
	std::unordered_set<AssetTrackingTuple*, std::hash<AssetTrackingTuple*>, AssetTrackingTuplePtrEqual>	assetTrackerTuplesCache;
};

#endif
