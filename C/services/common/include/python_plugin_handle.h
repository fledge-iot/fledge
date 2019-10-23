
#ifndef _PYTHON_PLUGIN_HANDLE_H
#define _PYTHON_PLUGIN_HANDLE_H
/*
 * Fledge Base plugin handle class
 *
 * Copyright (c) 2019 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Amandeep Singh Arora, Massimiliano Pinto
 */
#include <logger.h>
#include <vector>
#include <sstream>
#include <dlfcn.h>
#include <plugin_handle.h>
#include <Python.h>

typedef void* (*pluginResolveSymbolFn)(const char *, const std::string&);
typedef void (*pluginCleanupFn)(const std::string&);

/**
 * The PythonPluginHandle class is the base class used to represent an interface to
 * a plugin that is available as a python script
 */
class PythonPluginHandle : public PluginHandle
{
	public:
		// Base constructor
		PythonPluginHandle(const char *name, const char *path) : m_name(name) {};

		/**
		 * Base destructor
		 *    - Call cleanup on python plugin interface
		 *    - Close python plugin interface library handle
		 */
		~PythonPluginHandle()
		{
			if (!m_hndl)
			{
				return;
			}
			pluginCleanupFn cleanupFn =
				(pluginCleanupFn) dlsym(m_hndl, "PluginInterfaceCleanup");
			if (cleanupFn == NULL)
			{
				// Unable to find PluginInterfaceCleanup entry point
				Logger::getLogger()->error("Plugin library %s does not support %s function : %s",
							   m_interfaceObjName.c_str(),
							   "PluginInterfaceCleanup",
							   dlerror());
			}
			else
			{
				cleanupFn(m_name);
			}
			dlclose(m_hndl);
			m_hndl = NULL;
		};

		/**
		 * Gets function pointer from loaded python interface library that can
		 * be invoked to call 'sym' function in python plugin
		 *
		 * @param    sym	The symbol to fetch
		 */
		void *ResolveSymbol(const char* sym)
		{
			if (!m_hndl)
			{
				return NULL;
			}
			pluginResolveSymbolFn resolvSymFn =
				(pluginResolveSymbolFn) dlsym(m_hndl, "PluginInterfaceResolveSymbol");
			if (resolvSymFn == NULL)
			{
				// Unable to find PluginInterfaceResolveSymbol entry point
				Logger::getLogger()->error("Plugin library %s does not support "
							   "%s function : %s",
							   m_interfaceObjName.c_str(),
							   "PluginInterfaceResolveSymbol",
							   dlerror());
				return NULL;
			}
			void *rv = resolvSymFn(sym, m_name);
			if (!rv)
			{
				// Python filter plugins do not support plugin_start
				// just log a debug message
				if (m_type.compare(PLUGIN_TYPE_FILTER) == 0)
				{
					Logger::getLogger()->debug("PythonPluginHandle::ResolveSymbol "
								   "returning NULL for sym=%s, plugin %s, type %s",
								   sym,
								   m_name.c_str(),
								   m_type.c_str());
				}
				else
				{
					Logger::getLogger()->error("PythonPluginHandle::ResolveSymbol "
								   "returning NULL for sym=%s, plugin %s, type %s",
								   sym,
								   m_name.c_str(),
								   m_type.c_str());
				}
			}

			return rv;
		};

		/**
		 * Returns function pointer that can be invoked to call 'plugin_info'
		 * function in python plugin
		 */
		void *GetInfo()
		{
		        return (void *) ResolveSymbol("plugin_info");
		};

		// Return pointer to this class
		void *getHandle() { return this; }
	public:
		// The python plugin interface library shared object
		void*		m_hndl;
		// The interface library name to load
		std::string	m_interfaceObjName;

		// Set plugin name
		std::string	m_name;

		// plugin type
		std::string	m_type;
};

#endif
