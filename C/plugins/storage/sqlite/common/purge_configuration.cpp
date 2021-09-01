/*
 * Fledge Fledge Configuration management.
 *
 * Copyright (c) 2021 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */

#include <purge_configuration.h>
#include <logger.h>

using namespace std;

PurgeConfiguration *PurgeConfiguration::m_instance = 0;

/**
 * Constructor for the purge configurtion class
 */
PurgeConfiguration::PurgeConfiguration() : m_minimum(0)
{
}

/**
 * Destructor for the purge configurtion class
 */
PurgeConfiguration::~PurgeConfiguration()
{
}

/**
 * Return the singleton instance of the PurgeConfiguration class
 * for this plugin
 *
 * @return PurgeConfiguration* singleton instance
 */
PurgeConfiguration *PurgeConfiguration::getInstance()
{
	if (m_instance == 0)
	{
		m_instance = new PurgeConfiguration();
	}
	return m_instance;
}

/**
 * Add an asset to the exclusion list
 *
 * @param asset the asset to add to the exclusion list
 */
void PurgeConfiguration::exclude(const string& asset)
{
	Logger::getLogger()->debug("'%s' added to exclusion list", asset.c_str());
	m_exclude.push_back(asset);
}

/**
 * Check if the named asset appears in the exclusion list
 *
 * @param asset	Asset to check for exclusion
 * @return True if the asset is excluded
 */
bool PurgeConfiguration::isExcluded(const string& asset)
{
	for (auto it = m_exclude.cbegin(); it != m_exclude.cend(); it++)
	{
		if (it->compare(asset) == 0)
		{
			return true;
		}
	}
	return false;
}

/**
 * Set the minimum number of rows to retian for each asset
 *
 * @param minimum Minimum number of rows to retain
 */
void PurgeConfiguration::minimumRetained(uint32_t minimum)
{
	m_minimum = minimum;
}
