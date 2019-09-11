
#ifndef _FILTER_PYTHON_PLUGIN_HANDLE_H
#define _FILTER_PYTHON_PLUGIN_HANDLE_H
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
class FilterPythonPluginHandle : public PythonPluginHandle
{
	public:
		FilterPythonPluginHandle(const char *name, const char *path);
};

#endif

