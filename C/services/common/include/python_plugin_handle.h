
#ifndef _PYTHON_PLUGIN_HANDLE_H
#define _PYTHON_PLUGIN_HANDLE_H
/*
 * FogLAMP plugin handle related
 *
 * Copyright (c) 2018 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Amandeep Singh Arora
 */
#include <logger.h>
#include <vector>
#include <sstream>
#include <dlfcn.h>
#include <plugin_handle.h>
#include <Python.h>

/**
 * The PythonPluginHandle class is used to represent an interface to 
 * a plugin that is available as a python script
 */
class PythonPluginHandle : public PluginHandle
{
	public:
		PythonPluginHandle(const char *name, const char *path);
		~PythonPluginHandle();
		void *GetInfo();
		void *ResolveSymbol(const char* sym);
		void *getHandle() { return this; }
};

#endif

