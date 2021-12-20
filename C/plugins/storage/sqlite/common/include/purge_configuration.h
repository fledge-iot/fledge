#ifndef _PURGE_CONFIGURATION_H
#define _PURGE_CONFIGURATION_H
/*
 * Fledge storage service - Purge configuration
 *
 * Copyright (c) 2021 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <string>
#include <vector>

class PurgeConfiguration {
	public:
		static PurgeConfiguration	*getInstance();
		void				exclude(const std::string& asset);
		bool				hasExclusions() { return m_exclude.size() != 0; };
		bool				isExcluded(const std::string& asset);
		void				minimumRetained(uint32_t minimum);
		uint32_t			getMinimumRetained() { return m_minimum; };
	private:
		PurgeConfiguration();
		~PurgeConfiguration();
	private:
		static PurgeConfiguration	*m_instance;
		std::vector<std::string>	m_exclude;
		uint32_t			m_minimum;
};

#endif
