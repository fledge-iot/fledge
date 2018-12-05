
#ifndef _PLUGIN_HANDLE_H
#define _PLUGIN_HANDLE_H
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

#include <Python.h>

//typedef PLUGIN_INFORMATION *(*func_t)();

//#define PYTHON_FILTERS_PATH "/scripts"

/**
 * The PluginHandle class is used to represent an opaque handle to a 
 * plugin instance
 */
class PluginHandle
{
	public:
		PluginHandle() {}
		~PluginHandle() {}
		virtual void *GetInfo() = 0;
		virtual void *ResolveSymbol(const char* sym) = 0;
		virtual void *openHandle(const char *filepath) = 0;
		virtual void closeHandle() = 0;
	private:
		PLUGIN_HANDLE handle;
};

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
		void *openHandle(const char *) { return handle; }
		void closeHandle() {}
	private:
		PLUGIN_HANDLE handle; // pointer returned by dlopen on plugin shared lib
};

class PythonPluginHandle : public PluginHandle
{
	public:
		PythonPluginHandle(const char *name, const char *path);
		~PythonPluginHandle();
		void *GetInfo();
		void *ResolveSymbol(const char* sym);
		void *openHandle(const char *) { return this; }
		void closeHandle() { }
	private:
		//PLUGIN_HANDLE handle; // pointer returned by dlopen on plugin shared lib
		//std::unordered_map<std::string, void*) dispatchTable;
		//PyObject* pModule;
};



#endif

