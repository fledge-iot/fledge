/**
 * FogLAMP rule plugin class
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Massimiliano Pinto
 */

#include <rule_plugin.h>

using namespace std;


// RulePlugin constructor
RulePlugin::RulePlugin(const std::string& name,
		       PLUGIN_HANDLE handle) : Plugin(handle), m_name(name)
{
	// Setup the function pointers to the plugin
	pluginInit = (PLUGIN_HANDLE (*)(const ConfigCategory *))
					manager->resolveSymbol(handle,
							       "plugin_init");
	pluginShutdownPtr = (void (*)(PLUGIN_HANDLE))
				      manager->resolveSymbol(handle,
							     "plugin_shutdown");
	pluginTriggersPtr = (string (*)(PLUGIN_HANDLE))
					manager->resolveSymbol(handle, "plugin_triggers");

	pluginEvalPtr = (bool (*)(PLUGIN_HANDLE,
				  const string& assetValues))
				  manager->resolveSymbol(handle, "plugin_eval");

	// Persist data initialised
	m_plugin_data = NULL;
}

//RulePlugin destructor
RulePlugin::~RulePlugin()
{
	delete m_plugin_data;
}

/**
 * Call the loaded plugin "plugin_init" method
 *
 * @param config	The filter configuration
 * @return		The PLUGIN_HANDLE object
 */
PLUGIN_HANDLE RulePlugin::init(const ConfigCategory& config)
{
	m_instance = this->pluginInit(&config);
	return (m_instance ? &m_instance : NULL);
}

/**
 * Call the loaded plugin "plugin_shutdown" method
 */
void RulePlugin::shutdown()
{
	if (this->pluginShutdownPtr)
	{
		return this->pluginShutdownPtr(m_instance);
	}
}

/**
 * Call the loaded plugin "plugin_triggers" method
 *
 * @return		The JSON document, as string
 *			that describes the rule triggers.
 */
string RulePlugin::triggers()
{
	string ret = "";
	if (this->pluginTriggersPtr)
	{
		ret = this->pluginTriggersPtr(m_instance);
	}
	return ret;
}

/**
 * Call the loaded plugin "plugin_eval" method
 *
 * @param assetValues	The JSON document, as string
 *			that contains the set of asset values
 *			to evaluate.
 * @return		True if the rule was triggered,
 *			false otherwise.
 */
bool RulePlugin::eval(const string& assetValues)
{
	bool ret = false;
	if (this->pluginEvalPtr)
	{
		ret = this->pluginEvalPtr(m_instance, assetValues);
	}
	return ret;
}
