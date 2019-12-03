
#ifndef _NOTIFICATION_PYTHON_PLUGIN_HANDLE_H
#define _NOTIFICATION_PYTHON_PLUGIN_HANDLE_H
/*
 * Fledge Notification Python plugin handle related
 *
 * Copyright (c) 2019 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Massimiliano Pinto
 */
#include <logger.h>
#include <vector>
#include <sstream>
#include <dlfcn.h>
#include <python_plugin_handle.h>

/**
 * The PythonPluginHandle class is used to represent an interface to 
 * a plugin that is available as a python script
 */
class NotificationPythonPluginHandle : public PythonPluginHandle
{
	public:
		NotificationPythonPluginHandle(const char *name, const char *path);
};

#endif

