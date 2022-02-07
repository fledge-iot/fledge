#ifndef _NORTH_PLUGIN
#define _NORTH_PLUGIN
/*
 * Fledge north service.
 *
 * Copyright (c) 2020 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */

#include <plugin.h>
#include <plugin_manager.h>
#include <config_category.h>
#include <string>
#include <reading.h>

typedef void (*INGEST_CB)(void *, Reading);
typedef void (*INGEST_CB2)(void *, std::vector<Reading *>*);

/**
 * Class that represents a north plugin.
 *
 * The purpose of this class is to hide the use of the pointers into the
 * dynamically loaded plugin and wrap the interface into a class that
 * can be used directly in the north subsystem.
 *
 * This is achieved by having a set of private member variables which are
 * the pointers to the functions in the plugin, and a set of public methods
 * that will call these functions via the function pointers.
 */
class NorthPlugin : public Plugin {

public:
	NorthPlugin(PLUGIN_HANDLE handle, const ConfigCategory& category);
	~NorthPlugin();

	uint32_t	send(const std::vector<Reading *>& readings);
	void		reconfigure(const std::string&);
	void		shutdown();
	bool		persistData() { return info->options & SP_PERSIST_DATA; };
	void		start();
	void		startData(const std::string& pluginData);
	std::string	shutdownSaveData();
	bool		hasControl() { return info->options & SP_CONTROL; };
	void		pluginRegister(bool ( *write)(char *name, char *value, ControlDestination destination, ...),
				int (* operation)(char *operation, int paramCount, char *names[], char *parameters[], ControlDestination destination, ...));

private:
	PLUGIN_HANDLE	m_instance;
	uint32_t	(*pluginSendPtr)(PLUGIN_HANDLE, const std::vector<Reading *>& readings);
	void		(*pluginReconfigurePtr)(PLUGIN_HANDLE*,
					        const std::string& newConfig);
	void		(*pluginShutdownPtr)(PLUGIN_HANDLE);
	std::string	(*pluginShutdownDataPtr)(const PLUGIN_HANDLE);
	void		(*pluginStartPtr)(PLUGIN_HANDLE);
	void		(*pluginStartDataPtr)(PLUGIN_HANDLE,
					      const std::string& pluginData);
	void		(*pluginRegisterPtr)(PLUGIN_HANDLE handle,
				bool ( *write)(char *name, char *value, ControlDestination destination, ...),
				int (* operation)(char *operation, int paramCount, char *names[], char *parameters[], ControlDestination destination, ...));
	
};

#endif
