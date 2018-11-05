/*
 * FogLAMP base FogLampFilter class
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Massimiliano Pinto
 */

#include <filter.h>

using namespace std;

/**
 * FogLampFilter constructor
 *
 * This class or a derived one has to be used
 * as return object from FogLAMP filters C interface "plugin_init"A
 *
 * @param filterName	The filter plugin name
 * @param filterConfig	The filter plugin configuration
 * @param outHandle	A handle passed to the filter output stream function
 * @param output	The The output stream function pointer
 */
FogLampFilter::FogLampFilter(const string& filterName,
			     ConfigCategory& filterConfig,
			     OUTPUT_HANDLE *outHandle,
			     OUTPUT_STREAM output) : m_name(filterName),
						     m_config(filterConfig),
						     m_enabled(false)
{
	m_data = outHandle;
	m_func = output;

	// Set the enable flag
	if (m_config.itemExists("enable"))
	{
		m_enabled = m_config.getValue("enable").compare("true") == 0 ||
			    m_config.getValue("enable").compare("True") == 0;
	}
}
