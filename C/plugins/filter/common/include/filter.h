#ifndef _FOGLAMP_FITER_H
#define _FOGLAMP_FITER_H
/*
 * FogLAMP base FogLampFilter class
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Massimiliano Pinto
 */

#include <string>
#include <config_category.h>
#include <filter_plugin.h>

class FogLampFilter{
	public:
		FogLampFilter(const std::string& filterName,
			      ConfigCategory& filterConfig,
			      OUTPUT_HANDLE *outHandle,
			      OUTPUT_STREAM output);
		~FogLampFilter() {};
		const std::string&
				getName() const { return m_name; };
		bool		isEnabled() const { return m_enabled; };
		ConfigCategory& getConfig() { return m_config; };
	public:
		OUTPUT_HANDLE*	m_data;
		OUTPUT_STREAM	m_func;
	private:
		std::string	m_name;
		ConfigCategory	m_config;
		bool		m_enabled;
};

#endif
