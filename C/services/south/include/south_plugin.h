#ifndef _SOUTH_PLUGIN
#define _SOUTH_PLUGIN
/*
 * Fledge south service.
 *
 * Copyright (c) 2018 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */

#include <plugin.h>
#include <plugin_manager.h>
#include <config_category.h>
#include <string>
#include <reading_set.h>

typedef void (*INGEST_CB)(void *, Reading);
typedef void (*INGEST_CB2)(void *, std::vector<Reading *>*);

/**
 * Class that represents a south plugin.
 *
 * The purpose of this class is to hide the use of the pointers into the
 * dynamically loaded plugin and wrap the interface into a class that
 * can be used directly in the south subsystem.
 *
 * This is achieved by having a set of private member variables which are
 * the pointers to the functions in the plugin, and a set of public methods
 * that will call these functions via the function pointers.
 */
class SouthPlugin : public Plugin {

public:
	SouthPlugin(PLUGIN_HANDLE handle, const ConfigCategory& category);
	~SouthPlugin();

	Reading		poll();
	ReadingSet*	pollV2();
	void		start();
	void		reconfigure(const std::string&);
	void		shutdown();
	void		registerIngest(INGEST_CB, void *);
	void		registerIngestV2(INGEST_CB2, void *);
	bool		isAsync() { return info->options & SP_ASYNC; };
	bool		hasControl() { return info->options & SP_CONTROL; };
	bool		persistData() { return info->options & SP_PERSIST_DATA; };
	void		startData(const std::string& pluginData);
	std::string	shutdownSaveData();
	bool		write(const std::string& name, const std::string& value);
	bool		operation(const std::string& name, std::vector<PLUGIN_PARAMETER *>& );
private:
	PLUGIN_HANDLE	instance;
	bool		m_started; // Plugin started indicator, for async plugins
	void		(*pluginStartPtr)(PLUGIN_HANDLE);
	Reading		(*pluginPollPtr)(PLUGIN_HANDLE);
	std::vector<Reading*>* (*pluginPollPtrV2)(PLUGIN_HANDLE);
	void		(*pluginReconfigurePtr)(PLUGIN_HANDLE*,
					        const std::string& newConfig);
	void		(*pluginShutdownPtr)(PLUGIN_HANDLE);
	void		(*pluginRegisterPtr)(PLUGIN_HANDLE, INGEST_CB, void *);
	void		(*pluginRegisterPtrV2)(PLUGIN_HANDLE, INGEST_CB2, void *);
	std::string	(*pluginShutdownDataPtr)(const PLUGIN_HANDLE);
	void		(*pluginStartDataPtr)(PLUGIN_HANDLE,
					      const std::string& pluginData);
	bool		(*pluginWritePtr)(PLUGIN_HANDLE, const std::string& name, const std::string& value);
	bool		(*pluginOperationPtr)(const PLUGIN_HANDLE, const std::string& name, int count,
						PLUGIN_PARAMETER  **parameters);
};

#endif
