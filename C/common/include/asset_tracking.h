#ifndef _ASSET_TRACKING_H
#define _ASSET_TRACKING_H
/*
 * FogLAMP asset tracking related
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

/**
 * The AssetTrackingTuple class is used to represent an asset
 * tracking tuple. Hash function and == operator are defined for
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
		o << "service:" << m_serviceName << ", plugin:" << m_pluginName << ", asset:" << m_assetName << ", event:" << m_eventName;
		return o.str();
	}

	inline bool operator==(const AssetTrackingTuple& x) const
	{
		return ( x.m_serviceName==m_serviceName && x.m_pluginName==m_pluginName && x.m_assetName==m_assetName && x.m_eventName==m_eventName);
	}

	AssetTrackingTuple(const std::string& service, const std::string& plugin, 
								 const std::string& asset, const std::string& event) :
									m_serviceName(service), m_pluginName(plugin), 
									m_assetName(asset), m_eventName(event)
	{}
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

#endif
