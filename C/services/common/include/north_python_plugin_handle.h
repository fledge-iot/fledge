
#ifndef _NORTH_PYTHON_PLUGIN_HANDLE_H
#define _NORTH_PYTHON_PLUGIN_HANDLE_H
/*
 * Fledge plugin handle related
 *
 * Copyright (c) 2021 Dianomic Systems
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
 * The NorthPythonPluginHandle class is used to represent an interface to 
 * a South plugin that is available as a python script
 */
class NorthPythonPluginHandle : public PythonPluginHandle
{
	public:
		NorthPythonPluginHandle(const char *name, const char *path);
};

#endif

