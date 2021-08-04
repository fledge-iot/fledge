/*
 * Fledge plugin handle related
 *
 * Copyright (c) 2021 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Massimiliano Pinto
 */

#include <config_category.h>
#include <reading.h>
#include <logger.h>
#include <north_python_plugin_handle.h>

#define PYTHON_PLUGIN_INTF_LIB "libnorth-plugin-python-interface.so"

#define PRINT_FUNC	Logger::getLogger()->info("%s:%d", __FUNCTION__, __LINE__);

typedef PLUGIN_INFORMATION *(*pluginInitFn)(const char *pluginName, const char *path);

using namespace std;

/**
 * Constructor for NorthPythonPluginHandle
 *    - Load python interface library and initialize the interface
 *
 * @param    pluginName		The Python plugin name to load
 * @param    pluginPathName	The Python plugin path
 */
NorthPythonPluginHandle::NorthPythonPluginHandle(const char *pluginName,
						 const char *pluginPathName) :
						 PythonPluginHandle(pluginName, pluginPathName)
{
	// expecting this lib to be present in LD_LIBRARY_PATH:
	//same dir as where lib-services-common.so is present
	string libPath = PYTHON_PLUGIN_INTF_LIB;
	
	m_hndl = dlopen(libPath.c_str(), RTLD_NOW | RTLD_GLOBAL);
	if (!m_hndl)
	{
		Logger::getLogger()->error("PythonPluginHandle c'tor: dlopen failed for library '%s' : %s",
					   libPath.c_str(),
					   dlerror());
		return;
	}

	pluginInitFn initFn = (pluginInitFn) dlsym(m_hndl, "PluginInterfaceInit");
	if (initFn == NULL)
	{
		// Unable to find PluginInterfaceInit entry point
		Logger::getLogger()->error("Plugin library %s does not support %s function : %s",
					   libPath.c_str(),
					   "PluginInterfaceInit",
					   dlerror());
		dlclose(m_hndl);
		m_hndl = NULL;
		return;
	}

	// Initialise embedded Python and the interface
	void *ref = initFn(pluginName, pluginPathName);
	if (ref == NULL)
	{
		fprintf(stderr,
			"Plugin library %s : PluginInterfaceInit returned failure",
			libPath.c_str());
		dlclose(m_hndl);
		m_hndl = NULL;
		return;
	}

	// Set type
	m_type = PLUGIN_TYPE_NORTH;
}
