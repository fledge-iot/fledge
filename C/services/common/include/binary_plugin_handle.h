
#ifndef _BINARY_PLUGIN_HANDLE_H
#define _BINARY_PLUGIN_HANDLE_H
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
#include <unordered_map>
#include <dlfcn.h>
#include <plugin_api.h>
#include <plugin_handle.h>
#include <Python.h>

/**
 * The BinaryPluginHandle class is used to represent an interface to 
 * a plugin that is avaialble in a binary format
 */
class BinaryPluginHandle : public PluginHandle
{
	public:
		BinaryPluginHandle(const char *, const char *path)
			{
			Logger::getLogger()->info("BinaryPluginHandle c'tor: dlopen done for path='%s'", path);
			handle = dlopen(path, RTLD_LAZY);
			}
		~BinaryPluginHandle() { if (handle) dlclose(handle); }
		void *GetInfo()
			{
			Logger::getLogger()->info("BinaryPluginHandle::GetInfo(): dlsym for plugin_info");
			return dlsym(handle, "plugin_info"); 
			}
		void *ResolveSymbol(const char* sym)
			{
			Logger::getLogger()->info("BinaryPluginHandle::ResolveSymbol(): For sym='%s'", sym);
			return dlsym(handle, sym);
			}
		void *getHandle() { return handle; }
	private:
		PLUGIN_HANDLE handle; // pointer returned by dlopen on plugin shared lib
};

#endif

