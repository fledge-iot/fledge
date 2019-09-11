
#ifndef _PLUGIN_HANDLE_H
#define _PLUGIN_HANDLE_H
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
#include <vector>
#include <sstream>
#include <unordered_map>
#include <dlfcn.h>
#include <plugin_api.h>

/**
 * The PluginHandle class is used to represent an opaque handle to a 
 * plugin instance
 */
class PluginHandle
{
	public:
		PluginHandle() {}
		virtual ~PluginHandle() {}
		virtual void *GetInfo() = 0;
		virtual void *ResolveSymbol(const char* sym) = 0;
		virtual void *getHandle() = 0;
};

#endif

