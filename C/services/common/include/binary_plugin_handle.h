
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
#include <plugin_manager.h>

/**
 * The BinaryPluginHandle class is used to represent an interface to 
 * a plugin that is available in a binary format
 */
class BinaryPluginHandle : public PluginHandle
{
	public:
		// for the Storage plugin
		BinaryPluginHandle(const char *name, const char *path, tPluginType type) {
			dlerror();	// Clear the existing error
			handle = dlopen(path, RTLD_LAZY);
			if (!handle)
			{
				Logger::getLogger()->error("Unable to load storage plugin %s, %s",
						name, dlerror());
			}

			Logger::getLogger()->debug("%s - storage plugin / RTLD_LAZY - name :%s: path :%s:", __FUNCTION__, name, path);
		}

		// for all the others plugins
		BinaryPluginHandle(const char *name, const char *path)                   {
			dlerror();	// Clear the existing error
			handle = dlopen(path, RTLD_LAZY|RTLD_GLOBAL);
			if (!handle)
			{
				Logger::getLogger()->error("Unable to load plugin %s, %s",
						name, dlerror());
			}

			Logger::getLogger()->debug("%s - other plugin / RTLD_LAZY|RTLD_GLOBAL - name :%s: path :%s:", __FUNCTION__, name, path);
		}

		~BinaryPluginHandle() { if (handle) dlclose(handle); }
		void *GetInfo() { return dlsym(handle, "plugin_info"); }
		void *ResolveSymbol(const char* sym) { return dlsym(handle, sym); }
		void *getHandle() { return handle; }
	private:
		PLUGIN_HANDLE handle; // pointer returned by dlopen on plugin shared lib

};

#endif

