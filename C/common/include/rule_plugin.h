#ifndef _RULE_PLUGIN_H
#define _RULE_PLUGIN_H
/*
 * FogLAMP Rule plugin class.
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Massimiliano Pinto
 */
#include <plugin.h>
#include <plugin_manager.h>
#include <config_category.h>
#include <management_client.h>
#include <plugin_data.h>

// Rule Plugin class
class RulePlugin : public Plugin
{
	public:
		RulePlugin(const std::string& name,
			   PLUGIN_HANDLE handle);
	        ~RulePlugin();

		const std::string	getName() const { return m_name; };
		PLUGIN_HANDLE		init(const ConfigCategory& config);
		void			shutdown();
		bool			persistData() { return info->options & SP_PERSIST_DATA; };
		std::string		triggers();
		bool			eval(const std::string& assetValues);

	private:
		PLUGIN_HANDLE		(*pluginInit)(const ConfigCategory* config);
		void			(*pluginShutdownPtr)(PLUGIN_HANDLE);
		std::string		(*pluginTriggersPtr)(PLUGIN_HANDLE);
		bool			(*pluginEvalPtr)(PLUGIN_HANDLE,
							 const std::string& assetValues);

	public:
		// Persist plugin data
		PluginData*     	m_plugin_data;

	private:
		std::string     	m_name;
		PLUGIN_HANDLE   	m_instance;
};

#endif
