#ifndef _BINARY_PLUGIN_HANDLE_H
#define _BINARY_PLUGIN_HANDLE_H
/*
 * Fledge Binary Plugin
 *
 * Copyright (c) 2018-2025 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Amandeep Singh Arora
 */
#ifdef UNICODE
#undef UNICODE
#endif

#include <logger.h>
#include <dlfcn.h>
#include <plugin_handle.h>
#include <plugin_manager.h>

#ifdef __linux__
#define SharedLibOpen(path, flags) (PLUGIN_HANDLE) dlopen(path, flags)
#define SharedLibClose(handle) dlclose(handle)
#define SharedLibProcAddress(handle, sym) (void *)dlsym(handle, sym)
#define SharedLibErrorMsg dlerror
#define LoadLazy	RTLD_LAZY
#define LoadLazyGlobal RTLD_LAZY | RTLD_GLOBAL
#elif _WIN64
static char sharedLibMessage[128];
static char *getWindowsErrorMessage()
{
	DWORD errorCode = GetLastError();
	if (errorCode == 0)
	{
		sharedLibMessage[0] = '\0';
	}
	else
	{
		if (0 == FormatMessage(
			FORMAT_MESSAGE_FROM_SYSTEM | FORMAT_MESSAGE_IGNORE_INSERTS,
			NULL,
			errorCode,
			0,
			sharedLibMessage,
			sizeof(sharedLibMessage), NULL))
			{
				sharedLibMessage[0] = '\0';
			}
	}

	return sLibMessage;
}

#define SharedLibOpen(path, flags) (PLUGIN_HANDLE)LoadLibrary(path)
#define SharedLibClose(handle) FreeLibrary((HMODULE)handle)
#define SharedLibProcAddress(handle, sym) (void *)GetProcAddress(handle, sym)
#define SharedLibErrorMsg getWindowsErrorMessage
#define LoadLazy 0
#define LoadLazyGlobal 0
#endif

/**
 * The BinaryPluginHandle class is used to represent an interface to
 * a plugin that is available in a binary format
 */
class BinaryPluginHandle : public PluginHandle
{
public:
	// for the Storage plugin
	BinaryPluginHandle(const char *name, const char *path, tPluginType type)
	{
		SharedLibErrorMsg(); // Clear the existing error
		handle = SharedLibOpen(path, LoadLazy);
		if (!handle)
		{
			Logger::getLogger()->error("Unable to load storage plugin %s, %s",
									   name, SharedLibErrorMsg());
		}

		Logger::getLogger()->debug("%s - storage plugin / RTLD_LAZY - name :%s: path :%s:", __FUNCTION__, name, path);
	}

	// for all the others plugins
	BinaryPluginHandle(const char *name, const char *path)
	{
		SharedLibErrorMsg(); // Clear the existing error
		handle = SharedLibOpen(path, LoadLazyGlobal);
		if (!handle)
		{
			Logger::getLogger()->error("Unable to load plugin %s, %s",
									   name, SharedLibErrorMsg());
		}

		Logger::getLogger()->debug("%s - other plugin / RTLD_LAZY|RTLD_GLOBAL - name :%s: path :%s:", __FUNCTION__, name, path);
	}

	~BinaryPluginHandle()
	{
		if (handle)
		{
			SharedLibClose(handle);
		}
	}
	void *GetInfo() { return SharedLibProcAddress(handle, "plugin_info"); }
	void *ResolveSymbol(const char *sym) { return SharedLibProcAddress(handle, sym); }
	void *getHandle() { return handle; }

private:
	PLUGIN_HANDLE handle; // pointer returned by SharedLibOpen on plugin shared lib
};

#endif
