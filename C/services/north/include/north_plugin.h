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

	void		send(const std::vector<Reading *>& readings);
	void		reconfigure(const std::string&);
	void		shutdown();
	bool		persistData() { return info->options & SP_PERSIST_DATA; };
	void		startData(const std::string& pluginData);
	std::string	shutdownSaveData();

private:
	PLUGIN_HANDLE	instance;
	void		(*pluginSendPtr)(PLUGIN_HANDLE, const std::vector<Reading *>& readings);
	void		(*pluginReconfigurePtr)(PLUGIN_HANDLE*,
					        const std::string& newConfig);
	void		(*pluginShutdownPtr)(PLUGIN_HANDLE);
	std::string	(*pluginShutdownDataPtr)(const PLUGIN_HANDLE);
	void		(*pluginStartDataPtr)(PLUGIN_HANDLE,
					      const std::string& pluginData);
};

#endif
