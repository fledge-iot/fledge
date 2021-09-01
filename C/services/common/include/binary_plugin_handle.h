
#ifndef _BINARY_PLUGIN_HANDLE_H
#define _BINARY_PLUGIN_HANDLE_H
/*
 * Fledge plugin handle related
 *
 * Copyright (c) 2018 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Amandeep Singh Arora
 */
#include <logger.h>
#include <dlfcn.h>
#include <plugin_handle.h>

/**
 * The BinaryPluginHandle class is used to represent an interface to 
 * a plugin that is available in a binary format
 */
class BinaryPluginHandle : public PluginHandle
{
	public:
		BinaryPluginHandle(const char *, const char *path) { handle = dlopen(path, RTLD_LAZY|RTLD_GLOBAL); }
		~BinaryPluginHandle() { if (handle) dlclose(handle); }
		void *GetInfo() { return dlsym(handle, "plugin_info"); }
		void *ResolveSymbol(const char* sym) { return dlsym(handle, sym); }
		void *getHandle() { return handle; }
	private:
		PLUGIN_HANDLE handle; // pointer returned by dlopen on plugin shared lib
};

#endif

