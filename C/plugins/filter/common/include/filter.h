#ifndef _FLEDGE_FITER_H
#define _FLEDGE_FITER_H
/*
 * Fledge base FledgeFilter class
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

class FledgeFilter{
	public:
		FledgeFilter(const std::string& filterName,
			      ConfigCategory& filterConfig,
			      OUTPUT_HANDLE *outHandle,
			      OUTPUT_STREAM output);
		~FledgeFilter() {};
		const std::string&
				getName() const { return m_name; };
		bool		isEnabled() const { return m_enabled; };
		ConfigCategory& getConfig() { return m_config; };
		void		disableFilter() { m_enabled = false; };
		void		setConfig(const std::string& newConfig);
	public:
		OUTPUT_HANDLE*	m_data;
		OUTPUT_STREAM	m_func;
	protected:
		std::string	m_name;
		ConfigCategory	m_config;
		bool		m_enabled;
};

#endif
