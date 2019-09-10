/*
 * FogLAMP south plugin interface related
 *
 * Copyright (c) 2019 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Massimiliano Pinto
 */

#include <logger.h>
#include <config_category.h>
#include <reading.h>
#include <mutex>
#include <plugin_handle.h>
#include <Python.h>

#include <python_plugin_common_interface.h>

#define SHIM_SCRIPT_REL_PATH  "/python/foglamp/plugins/common/shim/"
#define SHIM_SCRIPT_NAME "notification_shim"

using namespace std;

extern "C" {

extern PLUGIN_INFORMATION *Py2C_PluginInfo(PyObject *);
extern void logErrorMessage();
extern PLUGIN_INFORMATION *plugin_info_fn();
extern PLUGIN_HANDLE plugin_init_fn(ConfigCategory *);
extern void plugin_shutdown_fn(PLUGIN_HANDLE);

// Reconfigure entry point for rule and delivery plugings
void notification_plugin_reconfigure_fn(PLUGIN_HANDLE,
					const std::string&);
// Notification rule plugin entry points
std::string plugin_triggers_fn(PLUGIN_HANDLE handle);
bool plugin_eval_fn(PLUGIN_HANDLE handle,
		    const std::string& assetValues);
std::string plugin_reason_fn(PLUGIN_HANDLE handle);
//Notificztion deelivery plugin entry point
bool plugin_deliver_fn(PLUGIN_HANDLE handle,
			const std::string& deliveryName,
			const std::string& notificationName,
			const std::string& triggerReason,
			const std::string& customMessage);

/**
 * Constructor for PythonPluginHandle
 *    - Load python interpreter
 *    - Set sys.path and sys.argv
 *    - Import shim layer script and pass plugin name in argv[1]
 *    - Set plygin_type (notificationRule or notificationDelivery in rgv[2]
 *
 * @param    pluginName		The plugin name to load
 * @param    pluginPathName	The plugin pathname
 * @return			Python object pointer
 *				of loaded Python shim  file
 *				or NULL for errors
 */
void *PluginInterfaceInit(const char *pluginName, const char * pluginPathName)
{
	// Set plugin name for common-plugin-interfaces/python
	gPluginName = pluginName;
	// Get FOGLAMP_ROOT dir
	string foglampRootDir(getenv("FOGLAMP_ROOT"));

	string path = foglampRootDir + SHIM_SCRIPT_REL_PATH;
	string name(SHIM_SCRIPT_NAME);

	// Python 3.5  script name
	std::size_t found = path.find_last_of("/");
	string pythonScript = path.substr(found + 1);
	string shimLayerPath = path.substr(0, found);

	// Embedded Python 3.5 program name
	wchar_t *programName = Py_DecodeLocale(name.c_str(), NULL);
	Py_SetProgramName(programName);
	PyMem_RawFree(programName);

	string foglampPythonDir = foglampRootDir + "/python";

	// Embedded Python 3.5 initialisation
	if (!Py_IsInitialized())
	{
		Py_Initialize();
		PyEval_InitThreads();
		PyThreadState* save = PyEval_SaveThread(); // release Python GIT
	}

	PyGILState_STATE state = PyGILState_Ensure();

	Logger::getLogger()->info("NotificationPlugin PythonInterface %s:%d: "
				  "shimLayerPath=%s, shimFile=%s, "
				  "foglampPythonDir=%s, plugin '%s",
				   __FUNCTION__,
				   __LINE__,
				   shimLayerPath.c_str(),
				   name.c_str(),
				   foglampPythonDir.c_str(),
				   gPluginName.c_str());

	// Set Python path for embedded Python 3.5
	// Get current sys.path - borrowed reference
	PyObject* sysPath = PySys_GetObject((char *)"path");
	PyList_Append(sysPath, PyUnicode_FromString((char *) shimLayerPath.c_str()));
	PyList_Append(sysPath, PyUnicode_FromString((char *) foglampPythonDir.c_str()));

	// Set sys.argv for embedded Python 3.5
	int argc = 3;
	wchar_t* argv[3];
	argv[0] = Py_DecodeLocale("", NULL);
	argv[1] = Py_DecodeLocale(pluginName, NULL);
	// Extract plugin type from path
	string pluginType =
			strstr(pluginPathName, "/notificationDelivery/") != NULL ?
			"notificationDelivery" :
			"notificationRule";
	argv[2] = Py_DecodeLocale(pluginType.c_str(), NULL);

	Logger::getLogger()->debug("NotificationPlugin PythonInterface %s: "
				    "setting plugin type to '%s' for plugin '%s'",
				   __FUNCTION__,
				   pluginType.c_str(),
				   gPluginName.c_str());
	PySys_SetArgv(argc, argv);

	// 2) Import Python script
	PyObject* pModule = PyImport_ImportModule(name.c_str());

	// Check whether the Python module has been imported
	if (!pModule)
	{
		// Failure
		if (PyErr_Occurred())
		{
			logErrorMessage();
		}
		Logger::getLogger()->fatal("PluginInterfaceInit: cannot import Python script "
					   "'%s' from '%s' : pythonScript=%s, shimLayerPath=%s, plugin '%s'",
					   name.c_str(), path.c_str(),
					   pythonScript.c_str(),
					   shimLayerPath.c_str(),
					   gPluginName.c_str());
	}
	else
	{
		std::pair<std::map<string, PyObject*>::iterator, bool> ret;
		if (pythonModules)
		{
			// Add element
			ret = pythonModules->insert(pair<string, PyObject*>(string(pluginName), pModule));
		}

		// Check result
		if (!pythonModules ||
		    ret.second == false)
		{
			Logger::getLogger()->fatal("%s:%d: python module not added to the map "
						   "of loaded plugins, pModule=%p, plugin '%s'i, aborting.",
						   __FUNCTION__,
						   __LINE__,
						   pModule,
						   gPluginName.c_str());

			PyGILState_Release(state);
			Py_CLEAR(pModule);
			return NULL;
		}
		else
		{
			Logger::getLogger()->debug("%s:%d: python module loaded successfully, pModule=%p, plugin '%s'",
						   __FUNCTION__,
						   __LINE__,
						   pModule,
						   gPluginName.c_str());
		}
	}

	PyGILState_Release(state);

	return pModule;
}

/**
 * Returns function pointer that can be invoked to call '_sym' function
 * in python plugin
 */
void* PluginInterfaceResolveSymbol(const char *_sym)
{
	string sym(_sym);
	if (!sym.compare("plugin_info"))
		return (void *) plugin_info_fn;
	else if (!sym.compare("plugin_init"))
		return (void *) plugin_init_fn;
	else if (!sym.compare("plugin_shutdown"))
		return (void *) plugin_shutdown_fn;
	else if (!sym.compare("plugin_reconfigure"))
		return (void *) notification_plugin_reconfigure_fn;
	else if (!sym.compare("plugin_triggers"))
		return (void *) plugin_triggers_fn;
	else if (!sym.compare("plugin_eval"))
		return (void *) plugin_eval_fn;
	else if (!sym.compare("plugin_reason"))
		return (void *) plugin_reason_fn;
	else if (!sym.compare("plugin_deliver"))
		return (void *) plugin_deliver_fn;
	else
	{
		Logger::getLogger()->fatal("PluginInterfaceResolveSymbol can not find symbol '%s' "
					   "in the Notification Python plugin interface library, "
					   "loaded plugin '%s'",
					   _sym,
					   gPluginName.c_str());
		return NULL;
	}
}

/**
 * Invoke 'plugin_triggers' function in notification rule python plugin
 *
 * Returned JSON data will be used for notification data subscription
 * to FogLAMP storage service
 *
 * @param    handle	The plugin handle from plugin_init_fn
 * @return		JSON string with array of
 *			asset name and windom data evaluation
 */
string plugin_triggers_fn(PLUGIN_HANDLE handle)
{
	string ret = "{\"triggers\" : []}";
	if (!pythonModules)
	{
		Logger::getLogger()->error("pythonModules map is NULL "
					   "in plugin_triggers, plugin '%s'",
					   gPluginName.c_str());
		return ret;
	}

	auto it = pythonModules->find(gPluginName);
	if (it == pythonModules->end() ||
	    !it->second)
	{
		Logger::getLogger()->fatal("plugin_handle: plugin_triggers(): "
					   "pModule is NULL for plugin '%s'",
					   gPluginName.c_str());
		return ret;
	}

	if (!handle)
	{
		Logger::getLogger()->fatal("plugin_handle: plugin_triggers(): "
					   "handle is NULL for plugin '%s'",
					   gPluginName.c_str());
		return ret;
	}

	std::mutex mtx;
	lock_guard<mutex> guard(mtx);

	PyGILState_STATE state = PyGILState_Ensure();

	PyObject* pFunc;
	// Fetch required method in loaded object
	pFunc = PyObject_GetAttrString(it->second, "plugin_triggers");
	if (!pFunc)
	{
		Logger::getLogger()->fatal("Cannot find 'plugin_triggers' method "
					   "in loaded python module '%s'",
					   gPluginName.c_str());
		Py_CLEAR(pFunc);
		PyGILState_Release(state);
		return ret;
	}

	if (!pFunc || !PyCallable_Check(pFunc))
	{
		// Failure
		if (PyErr_Occurred())
		{
			logErrorMessage();
		}

		Logger::getLogger()->fatal("Cannot call method 'plugin_triggers' "
					    "in loaded python module '%s'",
					    gPluginName.c_str());
		Py_CLEAR(pFunc);
	
		PyGILState_Release(state);
		return ret;
	}

	// Call Python method passing an object
	PyObject* pReturn = PyObject_CallFunction(pFunc,
						  "O",
						  handle);

	Py_CLEAR(pFunc);

	// Handle return
	if (!pReturn)
	{
		Logger::getLogger()->error("Called python script method 'plugin_triggers' : "
					    "error while getting result object, plugin '%s'",
					    gPluginName.c_str());
		logErrorMessage();
	}

	// Return C++ string
	if (pReturn &&
	    (PyBytes_Check(pReturn) || PyUnicode_Check(pReturn)))
	{
		ret = string(PyUnicode_AsUTF8(pReturn));
        }

	PyGILState_Release(state);
	return ret;
}

/**
 * Function to invoke 'plugin_reason' function in notification rule python plugin
 *
 * @param    handle	The plugin handle from plugin_init_fn
 * @return		JSON string with trigger reason
 */
std::string plugin_reason_fn(PLUGIN_HANDLE handle)
{
	string ret = "{\"reason\" : \"errored\"}";
	if (!pythonModules)
	{
		Logger::getLogger()->error("pythonModules map is NULL "
					   "in plugin_reason, plugin '%s'",
					   gPluginName.c_str());
		return ret;
	}

	auto it = pythonModules->find(gPluginName);
	if (it == pythonModules->end() ||
	    !it->second)
	{
		Logger::getLogger()->fatal("plugin_handle: plugin_reason(): "
					   "pModule is NULL for plugin '%s'",
					   gPluginName.c_str());
		return ret;
	}

	if (!handle)
	{
		Logger::getLogger()->fatal("plugin_handle: plugin_reason(): "
					   "handle is NULL for plugin '%s'",
					   gPluginName.c_str());
		return ret;
	}

	std::mutex mtx;
	lock_guard<mutex> guard(mtx);

	PyObject* pFunc;
	PyGILState_STATE state = PyGILState_Ensure();

	// Fetch required method in loaded object
	pFunc = PyObject_GetAttrString(it->second, "plugin_reason");
	if (!pFunc)
	{
		Logger::getLogger()->fatal("Cannot find 'plugin_reason' method "
					   "in loaded python module '%s'",
					   gPluginName.c_str());
		Py_CLEAR(pFunc);
		PyGILState_Release(state);
		return ret;
	}

	if (!pFunc || !PyCallable_Check(pFunc))
	{
		// Failure
		if (PyErr_Occurred())
		{
			logErrorMessage();
		}

		Logger::getLogger()->fatal("Cannot call method 'plugin_reason' "
					    "in loaded python module '%s'",
					    gPluginName.c_str());
		Py_CLEAR(pFunc);
		PyGILState_Release(state);
		return ret;
	}

	// Call Python method passing an object
	PyObject* pReturn = PyObject_CallFunction(pFunc,
						  "O",
						  handle);

	Py_CLEAR(pFunc);

	// Handle return
	if (!pReturn)
	{
		Logger::getLogger()->error("Called python script method 'plugin_reason' : "
					    "error while getting result object, plugin '%s'",
					    gPluginName.c_str());
		logErrorMessage();
	}

	// Return C++ string
	if (pReturn &&
	    (PyBytes_Check(pReturn) || PyUnicode_Check(pReturn)))
	{
		ret = std::string(PyUnicode_AsUTF8(pReturn));
	}
	PyGILState_Release(state);

	return ret;
}

/**
 * Function to invoke 'plugin_eval' function in notification rule python plugin
 *
 * @param    handle		The plugin handle from plugin_init_fn
 * @param    assetValues	JSON string with asset data to evaluate
 * @return			True if rule evaluation triggers, false otherwise
 */
bool plugin_eval_fn(PLUGIN_HANDLE handle,
		    const std::string& assetValues)
{
	bool ret = false;
	if (!pythonModules)
	{
		Logger::getLogger()->error("pythonModules map is NULL "
					   "in plugin_eval, plugin '%s'",
					   gPluginName.c_str());
		return ret;
	}

	auto it = pythonModules->find(gPluginName);
	if (it == pythonModules->end() ||
	    !it->second)
	{
		Logger::getLogger()->fatal("plugin_handle: plugin_eval(): "
					   "pModule is NULL for plugin '%s'",
					   gPluginName.c_str());
		return ret;
	}

	if (!handle)
	{
		Logger::getLogger()->fatal("plugin_handle: plugin_eval(): "
					   "handle is NULL for plugin '%s'",
					   gPluginName.c_str());
		return ret;
	}

	std::mutex mtx;
	lock_guard<mutex> guard(mtx);

	PyObject* pFunc;
	PyGILState_STATE state = PyGILState_Ensure();

	// Fetch required method in loaded object
	pFunc = PyObject_GetAttrString(it->second, "plugin_eval");
	if (!pFunc)
	{
		Logger::getLogger()->fatal("Cannot find 'plugin_eval' method "
					   "in loaded python module '%s'",
					   gPluginName.c_str());
		Py_CLEAR(pFunc);
		PyGILState_Release(state);
		return ret;
	}

	if (!pFunc || !PyCallable_Check(pFunc))
	{
		// Failure
		if (PyErr_Occurred())
		{
			logErrorMessage();
		}

		Logger::getLogger()->fatal("Cannot call method 'plugin_eval' "
					    "in loaded python module '%s'",
					    gPluginName.c_str());
		Py_CLEAR(pFunc);
		PyGILState_Release(state);
		return ret;
	}

	// Call Python method passing an object and the data as C string
	PyObject* pReturn = PyObject_CallFunction(pFunc,
						  "Os",
						  handle,
						  assetValues.c_str());

	Py_CLEAR(pFunc);

	// Handle return
	if (!pReturn)
	{
		Logger::getLogger()->error("Called python script method 'plugin_eval' : "
					   "error while getting result object, plugin '%s'",
					   gPluginName.c_str());
		logErrorMessage();
	}
	else
	{
		// check bool abd return true or false
		if (PyBool_Check(pReturn))
		{
			ret = PyObject_IsTrue(pReturn);
		}
	}
	PyGILState_Release(state);

	return ret;
}

/**
 * Function to invoke 'plugin_reconfigure' function in python plugin
 *
 * @param    handle     The plugin handle from plugin_init_fn
 * @param    config     The new configuration, as string
 */
void notification_plugin_reconfigure_fn(PLUGIN_HANDLE handle,
					const std::string& config)
{
	if (!pythonModules)
	{
		Logger::getLogger()->error("pythonModules map is NULL "
					   "in notification_plugin_reconfigure_fn, plugin '%s'",
					   gPluginName.c_str());
		return;
	}

	auto it = pythonModules->find(gPluginName);
	if (it == pythonModules->end() ||
	    !it->second)
	{
		Logger::getLogger()->fatal("plugin_handle: plugin_reconfigure(): "
					   "pModule is NULL for plugin '%s'",
					   gPluginName.c_str());
		return;
	}

	if (!handle)
	{
		Logger::getLogger()->fatal("plugin_handle: plugin_reconfigure(): "
					   "handle is NULL for plugin '%s'",
					   gPluginName.c_str());
		return;
	}

	std::mutex mtx;
	lock_guard<mutex> guard(mtx);

	PyGILState_STATE state = PyGILState_Ensure();

	Logger::getLogger()->debug("plugin_handle: plugin_reconfigure(): "
				   "pModule=%p, handle=%p, plugin '%s'",
				   it->second,
				   handle,
				   gPluginName.c_str());

	PyObject* pFunc;
	// Fetch required method in loaded object
	pFunc = PyObject_GetAttrString(it->second, "plugin_reconfigure");
	if (!pFunc)
	{       
		Logger::getLogger()->fatal("Cannot find method 'plugin_reconfigure' "
					   "in loaded python module '%s'",
					   gPluginName.c_str());
	}

	if (!pFunc || !PyCallable_Check(pFunc))
	{
		// Failure
		if (PyErr_Occurred())
		{
			logErrorMessage();
		}

		Logger::getLogger()->fatal("Cannot call method 'plugin_reconfigure' "
					   "in loaded python module '%s'",
					   gPluginName.c_str());
					   Py_CLEAR(pFunc);
		PyGILState_Release(state);
		return;
	}

	Logger::getLogger()->debug("plugin_reconfigure with %s", config.c_str());

	// Call Python method passing an object and a C string
	PyObject* pReturn = PyObject_CallFunction(pFunc,
						  "Os",
						  handle,
						  config.c_str());

	Py_CLEAR(pFunc);

	// Handle returned data
	if (!pReturn)
	{
		Logger::getLogger()->error("Called python script method plugin_reconfigure "
					   ": error while getting result object, plugin '%s'",
					   gPluginName.c_str());
		logErrorMessage();
	}
	else
	{
		PyObject* tmp = (PyObject *)handle;
		// Check current handle is Dict and pReturn is a Dict too
		if (PyDict_Check(tmp) && PyDict_Check(pReturn))
		{
			// Clear Dict content
			PyDict_Clear(tmp);
			// Populate hadnle Dict with new data in pReturn
			PyDict_Update(tmp, pReturn);
			// Remove pReturn ojbect
			Py_CLEAR(pReturn);

			Logger::getLogger()->debug("plugin_handle: plugin_reconfigure(): "
						    "got updated handle from python plugin=%p, plugin '%s'",
						    handle,
						    gPluginName.c_str());
		}
		else
		{
			Logger::getLogger()->error("plugin_handle: plugin_reconfigure(): "
						   "got object type '%s' instead of Python Dict, "
						   "python plugin=%p, plugin '%s'",
						   Py_TYPE(pReturn)->tp_name,
						   handle,
						   gPluginName.c_str());
		}
	}
	PyGILState_Release(state);
}

/**
 * Function to invoke 'plugin_deliver' function in
 * notification deliveryi python plugin
 *
 * @param    handle     	The plugin handle from plugin_init_fn
 * @param    handle		The plugin handle returned from plugin_init
 * @param    deliveryName	The delivery category name
 * @param    notificationName	The notification name
 * @param    triggerReason	The trigger reason for notification
 * @param    customMessage	The message from notification
 * @return			True is notification has been delivered,
 *				false otherwise
 */
bool plugin_deliver_fn(PLUGIN_HANDLE handle,
			const std::string& deliveryName,
			const std::string& notificationName,
			const std::string& triggerReason,
			const std::string& customMessage)
{
	bool ret = false;
	if (!pythonModules)
	{
		Logger::getLogger()->error("pythonModules map is NULL "
					   "in plugin_deliver, plugin '%s'",
					   gPluginName.c_str());
		return ret;
	}

	auto it = pythonModules->find(gPluginName);
	if (it == pythonModules->end() ||
	    !it->second)
	{
		Logger::getLogger()->fatal("plugin_handle: plugin_deliver(): "
					   "pModule is NULL for plugin '%s'",
					   gPluginName.c_str());
		return ret;
	}
	if (!handle)
	{
		Logger::getLogger()->fatal("plugin_handle: plugin_deliver(): "
					   "handle is NULL for plugin '%s'",
					   gPluginName.c_str());
		return ret;
	}

	std::mutex mtx;
	lock_guard<mutex> guard(mtx);

	PyObject* pFunc;
	PyGILState_STATE state = PyGILState_Ensure();

	// Fetch required method in loaded object
	pFunc = PyObject_GetAttrString(it->second, "plugin_deliver");
	if (!pFunc)
	{
		Logger::getLogger()->fatal("Cannot find 'plugin_deliver' method "
					   "in loaded python module '%s'",
					   gPluginName.c_str());
		Py_CLEAR(pFunc);
		PyGILState_Release(state);
		return ret;
	}

	if (!pFunc || !PyCallable_Check(pFunc))
	{
		// Failure
		if (PyErr_Occurred())
		{
			logErrorMessage();
		}

		Logger::getLogger()->fatal("Cannot call method 'plugin_deliver' "
					    "in loaded python module '%s'",
					    gPluginName.c_str());
		Py_CLEAR(pFunc);
		PyGILState_Release(state);
		return ret;
	}

	// Call Python method passing an object and the data as C string
	PyObject* pReturn = PyObject_CallFunction(pFunc,
						  "Ossss",
						  handle,
						  deliveryName.c_str(),
						  notificationName.c_str(),
						  triggerReason.c_str(),
						  customMessage.c_str());

	Py_CLEAR(pFunc);

	// Handle return
	if (!pReturn)
	{
		Logger::getLogger()->error("Called python script method 'plugin_deliver' : "
					   "error while getting result object, plugin '%s'",
					   gPluginName.c_str());
		logErrorMessage();
	}
	else
	{
		// check bool abd return true or false
		if (PyBool_Check(pReturn))
		{
			ret = PyObject_IsTrue(pReturn);
		}
	}

	PyGILState_Release(state);

	return ret;
}
}; // End of extern C
