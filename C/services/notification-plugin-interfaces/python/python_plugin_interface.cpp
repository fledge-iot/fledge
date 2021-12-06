/*
 * Fledge south plugin interface related
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
#include <pyruntime.h>
#include <Python.h>

#include <python_plugin_common_interface.h>

using namespace std;

extern "C" {

extern PLUGIN_INFORMATION *Py2C_PluginInfo(PyObject *);
extern void logErrorMessage();
extern bool numpyImportError;
extern PLUGIN_INFORMATION *plugin_info_fn();
extern PLUGIN_HANDLE plugin_init_fn(ConfigCategory *);
extern void plugin_shutdown_fn(PLUGIN_HANDLE);
extern void setImportParameters(string& shimLayerPath, string& fledgePythonDir);

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
	bool initPython = false;
	// Set plugin name for common-plugin-interfaces/python
	gPluginName = pluginName;

	string name("notification" + string(SHIM_SCRIPT_POSTFIX));

	string shimLayerPath;
	string fledgePythonDir;

	// Python 3.x set parameters for import
	setImportParameters(shimLayerPath, fledgePythonDir);

	// Embedded Python 3.x program name
	wchar_t *programName = Py_DecodeLocale(name.c_str(), NULL);
	Py_SetProgramName(programName);
	PyMem_RawFree(programName);

	PythonRuntime::getPythonRuntime();

	PyThreadState* newInterp = NULL;

	 // Acquire GIL
	PyGILState_STATE state = PyGILState_Ensure();

	// New Python interpreter
	if (!initPython)
	{
		newInterp = Py_NewInterpreter();
		if (!newInterp)
		{
			Logger::getLogger()->fatal("NotificationPlugin PluginInterfaceInit "
						   "Py_NewInterpreter failure for plugin '%s': ",
						   pluginName);
			logErrorMessage();

			PyGILState_Release(state);
			return NULL;
		}

		Logger::getLogger()->debug("NotificationPlugin PluginInterfaceInit "
					   "has added a new Python interpreter '%p', "
					   "plugin '%s'",
					   newInterp,
					   pluginName);
	}

	Logger::getLogger()->debug("NotificationPlugin PythonInterface %s:%d: "
				  "shimLayerPath=%s, shimFile=%s, plugin '%s",
				   __FUNCTION__,
				   __LINE__,
				   shimLayerPath.c_str(),
				   name.c_str(),
				   pluginName);

	// Set Python path for embedded Python 3.x
	// Get current sys.path - borrowed reference
	PyObject* sysPath = PySys_GetObject((char *)"path");
	PyList_Append(sysPath, PyUnicode_FromString((char *) shimLayerPath.c_str()));
	PyList_Append(sysPath, PyUnicode_FromString((char *) fledgePythonDir.c_str()));

	// Set sys.argv for embedded Python 3.x
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

	Logger::getLogger()->debug("NotificationPlugin PluginInterfaceInit %s: "
				    "setting plugin type to '%s' for plugin '%s'",
				   __FUNCTION__,
				   pluginType.c_str(),
				   pluginName);
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

		Logger::getLogger()->fatal("NotificationPlugin PluginInterfaceInit: "
					   "cannot import Python shim script '%s' "
					   "from shimLayerPath=%s, plugin '%s'",
					   name.c_str(),
					   shimLayerPath.c_str(),
					   pluginName);
		if (numpyImportError)
		{
			Logger::getLogger()->warn("Above import error is possibly caused by loading of Numpy library (or any library like Pandas/SciPy etc. that uses numpy internally) " \
				"in python plugins multiple times (once per plugin, but same process) and that is a known issue because Numpy does not support working with multiple " \
				"Python sub-interpreters in the same process. Also see: https://github.com/numpy/numpy/issues/14384");
			numpyImportError = false;
		}
	}
	else
	{
		std::pair<std::map<string, PythonModule*>::iterator, bool> ret;
		PythonModule* newModule = NULL;
		if (pythonModules)
		{
			string type = strstr(pluginPathName, PLUGIN_TYPE_NOTIFICATION_RULE) != NULL ?
					PLUGIN_TYPE_NOTIFICATION_RULE :
					PLUGIN_TYPE_NOTIFICATION_DELIVERY;

			// Add module into pythonModules, pluginName is the key
			if ((newModule = new PythonModule(pModule,
							  initPython,
							  string(pluginName),
							  type,
							  newInterp)) == NULL)
			{
				// Release lock
				PyEval_ReleaseThread(newInterp);

				Logger::getLogger()->fatal("NotificationPlugin PluginInterfaceInit "
							   "failed to create Python module "
							   "object, plugin '%s'",
							   pluginName);
				return NULL;
			}

			// Add element
			ret = pythonModules->insert(pair<string, PythonModule*>
				(string(pluginName), newModule));
		}

		// Check result
		if (!pythonModules ||
		    ret.second == false)
		{
			Logger::getLogger()->fatal("%s:%d: python module not added to the map "
						   "of loaded plugins, pModule=%p, plugin '%s', aborting.",
						   __FUNCTION__,
						   __LINE__,
						   pModule,
						   pluginName);

			// Cleanup
			Py_CLEAR(pModule);
			pModule = NULL;

			delete newModule;
			newModule = NULL;
		}
		else
		{
			Logger::getLogger()->debug("%s:%d: python module "
						   "loaded successfully, pModule=%p, plugin '%s'",
						   __FUNCTION__,
						   __LINE__,
						   pModule,
						   pluginName);
		}
	}

	// Release locks
	if (!initPython)
	{
		PyEval_ReleaseThread(newInterp);
	}
	else
	{
		PyGILState_Release(state);
	}

	// Return new Python module or NULL
	return pModule;
}

/**
 * Returns function pointer that can be invoked to call '_sym' function
 * in python plugin
 *
 * @param    _sym       Symbol name
 * @param    name       Plugin name
 * @return              function pointer to be invoked
 */
void* PluginInterfaceResolveSymbol(const char *_sym, const string& name)
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
					   name.c_str());
		return NULL;
	}
}

/**
 * Invoke 'plugin_triggers' function in notification rule python plugin
 *
 * Returned JSON data will be used for notification data subscription
 * to Fledge storage service
 *
 * @param    handle	The plugin handle from plugin_init_fn
 * @return		JSON string with array of
 *			asset name and windom data evaluation
 */
string plugin_triggers_fn(PLUGIN_HANDLE handle)
{
	string ret = "{\"triggers\" : []}";

	if (!handle)
	{
		Logger::getLogger()->fatal("plugin_handle: plugin_triggers(): "
					   "handle is NULL");
		return ret;
	}

	if (!pythonHandles)
	{
		Logger::getLogger()->error("pythonModules map is NULL "
					   "in plugin_triggers_fn, handle '%p'",
					   handle);
		return ret;
	}

	// Look for Python module for handle key
	auto it = pythonHandles->find(handle);
	if (it == pythonHandles->end() ||
	    !it->second ||
	    !it->second->m_module)
	{
		Logger::getLogger()->fatal("plugin_handle: plugin_triggers(): "
					   "pModule is NULL, plugin handle '%p'",
					   handle);
		return ret;
	}

	std::mutex mtx;
	lock_guard<mutex> guard(mtx);

	PyGILState_STATE state = PyGILState_Ensure();

	PyObject* pFunc;
	// Fetch required method in loaded object
	pFunc = PyObject_GetAttrString(it->second->m_module, "plugin_triggers");
	if (!pFunc)
	{
		Logger::getLogger()->fatal("Cannot find 'plugin_triggers' method "
					   "in loaded python module '%s'",
					   it->second->m_name.c_str());
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
					   it->second->m_name.c_str());
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
					   it->second->m_name.c_str());
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

	if (!handle)
	{
		Logger::getLogger()->fatal("plugin_handle: plugin_reason(): "
					   "handle is NULL");
		return ret;
	}

	if (!pythonHandles)
	{
		Logger::getLogger()->error("pythonModules map is NULL "
					   "in plugin_reason_fn, handle '%p'",
					   handle);
		return NULL;
	}

	// Look for Python module for handle key
	auto it = pythonHandles->find(handle);
	if (it == pythonHandles->end() ||
	    !it->second ||
	    !it->second->m_module)
	{
		Logger::getLogger()->fatal("plugin_handle: plugin_reason(): "
					   "pModule is NULL, plugin handle '%p'",
					   handle);
		return ret;
	}

	std::mutex mtx;
	lock_guard<mutex> guard(mtx);

	PyObject* pFunc;
	PyGILState_STATE state = PyGILState_Ensure();

	// Fetch required method in loaded object
	pFunc = PyObject_GetAttrString(it->second->m_module, "plugin_reason");
	if (!pFunc)
	{
		Logger::getLogger()->fatal("Cannot find 'plugin_reason' method "
					   "in loaded python module '%s'",
					   it->second->m_name.c_str());
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
					    it->second->m_name.c_str());
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
					   it->second->m_name.c_str());
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

	if (!handle)
	{
		Logger::getLogger()->fatal("plugin_handle: plugin_eval(): "
					   "handle is NULL");
		return ret;
	}

	if (!pythonHandles)
	{
		Logger::getLogger()->error("pythonModules map is NULL "
					   "in plugin_eval_fn, handle '%p'",
					   handle);
		return NULL;
	}

	// Look for Python module for handle key
	auto it = pythonHandles->find(handle);
	if (it == pythonHandles->end() ||
	    !it->second ||
	    !it->second->m_module)
	{
		Logger::getLogger()->fatal("plugin_handle: plugin_eval(): "
					   "pModule is NULL, plugin handle '%p'",
					   handle);
		return ret;
	}

	std::mutex mtx;
	lock_guard<mutex> guard(mtx);

	PyObject* pFunc;
	PyGILState_STATE state = PyGILState_Ensure();

	// Fetch required method in loaded object
	pFunc = PyObject_GetAttrString(it->second->m_module, "plugin_eval");
	if (!pFunc)
	{
		Logger::getLogger()->fatal("Cannot find 'plugin_eval' method "
					   "in loaded python module '%s'",
					   it->second->m_name.c_str());
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
					   it->second->m_name.c_str());
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
					   it->second->m_name.c_str());
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
	if (!handle)
	{
		Logger::getLogger()->fatal("plugin_handle: plugin_reconfigure(): "
					   "handle is NULL");
		return;
	}

	if (!pythonHandles)
	{
		Logger::getLogger()->error("pythonModules map is NULL "
					   "in plugin_reconfigure_fn, handle '%p'",
					   handle);
		return;
	}

	// Look for Python module for handle key
	auto it = pythonHandles->find(handle);
	if (it == pythonHandles->end() ||
	    !it->second ||
	    !it->second->m_module)
	{
		Logger::getLogger()->fatal("plugin_handle: plugin_reconfigure(): "
					   "pModule is NULL, plugin handle '%p'",
					   handle);
		return;
	}

	std::mutex mtx;
	lock_guard<mutex> guard(mtx);

	PyGILState_STATE state = PyGILState_Ensure();

	Logger::getLogger()->debug("plugin_handle: plugin_reconfigure(): "
				   "pModule=%p, handle=%p, plugin '%s'",
				   it->second->m_module,
				   handle,
				   it->second->m_name.c_str());

	PyObject* pFunc;
	// Fetch required method in loaded object
	pFunc = PyObject_GetAttrString(it->second->m_module, "plugin_reconfigure");
	if (!pFunc)
	{       
		Logger::getLogger()->fatal("Cannot find method 'plugin_reconfigure' "
					   "in loaded python module '%s'",
					   it->second->m_name.c_str());
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
					   it->second->m_name.c_str());
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
					   it->second->m_name.c_str());
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
						    it->second->m_name.c_str());
		}
		else
		{
			Logger::getLogger()->error("plugin_handle: plugin_reconfigure(): "
						   "got object type '%s' instead of Python Dict, "
						   "python plugin=%p, plugin '%s'",
						   Py_TYPE(pReturn)->tp_name,
						   handle,
						   it->second->m_name.c_str());
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

	if (!handle)
	{
		Logger::getLogger()->fatal("plugin_handle: plugin_deliver(): "
					   "handle is NULL");
		return ret;
	}

	if (!pythonHandles)
	{
		Logger::getLogger()->error("pythonModules map is NULL "
					   "in plugin_deliver_fn, handle '%p'",
					   handle);
		return NULL;
	}

	// Look for Python module for handle key
	auto it = pythonHandles->find(handle);
	if (it == pythonHandles->end() ||
	    !it->second ||
	    !it->second->m_module)
	{
		Logger::getLogger()->fatal("plugin_handle: plugin_deliver(): "
					   "pModule is NULL, plugin handle '%p'",
					   handle);
		return ret;
	}

	std::mutex mtx;
	lock_guard<mutex> guard(mtx);

	PyObject* pFunc;
	PyGILState_STATE state = PyGILState_Ensure();

	// Fetch required method in loaded object
	pFunc = PyObject_GetAttrString(it->second->m_module, "plugin_deliver");
	if (!pFunc)
	{
		Logger::getLogger()->fatal("Cannot find 'plugin_deliver' method "
					   "in loaded python module '%s'",
					   it->second->m_name.c_str());
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
					    it->second->m_name.c_str());
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
					   it->second->m_name.c_str());
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
