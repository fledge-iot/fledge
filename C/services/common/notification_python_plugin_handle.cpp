/*
 * Fledge Notification Python plugin handle related
 *
 * Copyright (c) 2019 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Massimiliano Pinto
 */

#include <config_category.h>
#include <reading.h>
#include <logger.h>
#include <notification_python_plugin_handle.h>

#define PYTHON_PLUGIN_INTF_LIB "libnotification-plugin-python-interface.so"

#define PRINT_FUNC	Logger::getLogger()->info("%s:%d", __FUNCTION__, __LINE__);

typedef PLUGIN_INFORMATION *(*pluginInitFn)(const char *pluginName, const char *path);

using namespace std;

/**
 * Constructor for NotificationPythonPluginHandle
 *    - Load python interface library and initialize the interface
 */
NotificationPythonPluginHandle::NotificationPythonPluginHandle(const char *pluginName,
								const char *pluginPathName) :
								PythonPluginHandle(pluginName, pluginPathName)
{
	// expecting this lib to be present in LD_LIBRARY_PATH:
	//same dir as where lib-services-common.so is present
	m_interfaceObjName = PYTHON_PLUGIN_INTF_LIB;

	// Open interface library object
	m_hndl = dlopen(m_interfaceObjName.c_str(), RTLD_NOW | RTLD_GLOBAL);
	if (!m_hndl)
	{
		Logger::getLogger()->error("NotificationPythonPluginHandle c'tor: dlopen failed for library '%s' : %s",
					   m_interfaceObjName.c_str(),
					   dlerror());
		return;
	}

	pluginInitFn initFn =
		(pluginInitFn) dlsym(m_hndl, "PluginInterfaceInit");
	if (initFn == NULL)
	{
		// Unable to find PluginInterfaceInit entry point
		Logger::getLogger()->error("Plugin library %s does not support %s function : %s",
					   m_interfaceObjName.c_str(),
					   "PluginInterfaceInit",
					   dlerror());
		dlclose(m_hndl);
		m_hndl = NULL;
		return;
	}

	// Initialise Python plugin object
	void *ref = initFn(pluginName, pluginPathName);
	if (ref == NULL)
	{
		fprintf(stderr,
			"Plugin library %s : PluginInterfaceInit returned failure",
			m_interfaceObjName.c_str());
		dlclose(m_hndl);
		m_hndl = NULL;
		return;
	}

	// Set type
	m_type = strstr(pluginPathName, PLUGIN_TYPE_NOTIFICATION_RULE) != NULL ?
		PLUGIN_TYPE_NOTIFICATION_RULE :
		PLUGIN_TYPE_NOTIFICATION_DELIVERY;
}
