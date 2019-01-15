/*
 * FogLAMP plugin handle related
 *
 * Copyright (c) 2018 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Amandeep Singh Arora
 */

#include <config_category.h>
#include <reading.h>
#include <logger.h>
#include <python_plugin_handle.h>

#define PYTHON_PLUGIN_INTF_LIB "libsouth-plugin-python-interface.so"

#define PRINT_FUNC	Logger::getLogger()->info("%s:%d", __FUNCTION__, __LINE__);

typedef PLUGIN_INFORMATION *(*pluginInitFn)(const char *pluginName, const char *path);
typedef void (*pluginCleanupFn)();
typedef void* (*pluginResolveSymbolFn)(const char *);
typedef void* (*pluginGetInfoFn)();

using namespace std;

void* hndl; // handle to the python plugin interface library shared object


/**
 * Constructor for PythonPluginHandle
 *    - Load python interface library and initialize the interface
 */
PythonPluginHandle::PythonPluginHandle(const char *pluginName, const char * _path)
{
	string libPath = PYTHON_PLUGIN_INTF_LIB; // expecting this lib to be present in LD_LIBRARY_PATH: same dir as where lib-services-common.so is present
	
	hndl = dlopen(libPath.c_str(), RTLD_NOW|RTLD_GLOBAL);
	if (!hndl)
	{
		Logger::getLogger()->error("PythonPluginHandle c'tor: dlopen failed for library '%s' : %s", libPath.c_str(), dlerror());
		return;
	}

	pluginInitFn initFn = (pluginInitFn) dlsym(hndl, "PluginInterfaceInit");
	if (initFn == NULL)
	{
	  // Unable to find PluginInterfaceInit entry point
	  Logger::getLogger()->error("Plugin library %s does not support %s function : %s", libPath.c_str(), "PluginInterfaceInit", dlerror());
	  dlclose(hndl);
	  return;
	}

	void *ref = initFn(pluginName, _path);
	if (ref == NULL)
	{
	  fprintf(stderr, "Plugin library %s : PluginInterfaceInit returned failure", libPath.c_str());
	  dlclose(hndl);
	  return;
	}
}

/**
 * Destructor for PythonPluginHandle
 *    - Call cleanup on python plugin interface
 *	  - Close python plugin interface library handle
 */
PythonPluginHandle::~PythonPluginHandle()
{
	pluginCleanupFn cleanupFn = (pluginCleanupFn) dlsym(hndl, "PluginInterfaceCleanup");
	if (cleanupFn == NULL)
	{
	  // Unable to find PluginInterfaceCleanup entry point
	  Logger::getLogger()->error("Plugin library %s does not support %s function : %s", PYTHON_PLUGIN_INTF_LIB, "PluginInterfaceCleanup", dlerror());
	}
	cleanupFn();
	dlclose(hndl);
}

/**
 * Gets function pointer from loaded python interface library that can
 * be invoked to call 'sym' function in python plugin
 */
void* PythonPluginHandle::ResolveSymbol(const char *sym)
{
	pluginResolveSymbolFn resolvSymFn = (pluginResolveSymbolFn) dlsym(hndl, "PluginInterfaceResolveSymbol");
	if (resolvSymFn == NULL)
	{
	  // Unable to find PluginInterfaceResolveSymbol entry point
	  Logger::getLogger()->error("Plugin library %s does not support %s function : %s", PYTHON_PLUGIN_INTF_LIB, "PluginInterfaceResolveSymbol", dlerror());
	}
	void *rv = resolvSymFn(sym);
	if (!rv)
		Logger::getLogger()->info("PythonPluginHandle::ResolveSymbol returning NULL for sym=%s", sym);

	return rv;
}

/**
 * Returns function pointer that can be invoked to call 'plugin_info'
 * function in python plugin
 */
void* PythonPluginHandle::GetInfo()
{
	return (void *) ResolveSymbol("plugin_info");
}
 
