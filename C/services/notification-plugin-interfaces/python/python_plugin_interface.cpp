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
#include <pythonreadingset.h>
#include <base64dpimage.h>
#include <base64databuffer.h>

#define PY_ARRAY_UNIQUE_SYMBOL  PyArray_API_FLEDGE
#include <numpy/npy_common.h>
#define NPY_NO_DEPRECATED_API NPY_1_7_API_VERSION
#include <numpy/ndarraytypes.h>
#include <numpy/ndarrayobject.h>

#undef NUMPY_IMPORT_ARRAY_RETVAL
#define NUMPY_IMPORT_ARRAY_RETVAL       0

using namespace std;

extern "C" {

extern PLUGIN_INFORMATION *Py2C_PluginInfo(PyObject *);
extern void logErrorMessage();
extern bool numpyImportError;
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

// Substitute string values with known data types
bool substituteObjects(PyObject *data, vector<PyObject*> &removeObjects);

/**
 * Constructor for PythonPluginHandle
 *    - Set sys.path and sys.argv
 *    - Set plugin_type (notificationRule or notificationDelivery
 *    - Load Python module for the plugin
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

	// Extract plugin type from path
	string pluginType = strstr(pluginPathName, PLUGIN_TYPE_NOTIFICATION_RULE) != NULL ?
					PLUGIN_TYPE_NOTIFICATION_RULE :
					PLUGIN_TYPE_NOTIFICATION_DELIVERY;

	string appPythonDir;

	string appRootDir(getenv("FLEDGE_ROOT"));
	appPythonDir = appRootDir + "/python";

	string notificationsRootPath = appPythonDir +
			string("/fledge/plugins/") +
			pluginType + "/" +
			string(pluginName);

	Logger::getLogger()->error("%s:%d:, filtersRootPath=%s",
				__FUNCTION__,
				__LINE__,
				notificationsRootPath.c_str());

	// Get Python runtime
	PythonRuntime::getPythonRuntime();

	// Acquire GIL
	PyGILState_STATE state = PyGILState_Ensure();

	Logger::getLogger()->debug("NotificationPlugin PluginInterfaceInit %s:%d: "
				"appPythonDir=%s, plugin '%s', type '%s'",
				__FUNCTION__,
				__LINE__,
				appPythonDir.c_str(),
				pluginName,
				pluginType.c_str());

	// Set Python path for embedded Python 3.x
	// Get current sys.path - borrowed reference
	PyObject* sysPath = PySys_GetObject((char *)"path");
	PyList_Append(sysPath,
			PyUnicode_FromString((char *)notificationsRootPath.c_str()));

    // Set sys.argv for embedded Python 3.5
	int argc = 2;
	wchar_t* argv[2];
	argv[0] = Py_DecodeLocale("", NULL);
	argv[1] = Py_DecodeLocale(pluginName, NULL);
	PySys_SetArgv(argc, argv);

	// Import plugin module
	PyObject *pModule = PyImport_ImportModule(pluginName);

	Logger::getLogger()->debug("%s:%d: pluginName=%s, type '%s', pModule=%p",
				__FUNCTION__,
				__LINE__,
				pluginName,
				pluginType.c_str(),
				pModule);

	// Check whether the Python module has been imported
	if (!pModule)
	{
		// Failure
		if (PyErr_Occurred())
		{
			logErrorMessage();
		}
		Logger::getLogger()->fatal("NotificationPlugin PluginInterfaceInit: "
					"cannot import Python module file "
					"from '%s', plugin '%s', type '%s'",
					pluginPathName,
					pluginName,
					pluginType.c_str());
	}
	else
	{
		std::pair<std::map<string, PythonModule*>::iterator, bool> ret;
		PythonModule* newModule = NULL;
		if (pythonModules)
		{
			// Add module into pythonModules, pluginName is the key
			if ((newModule = new PythonModule(pModule,
					initPython,
					string(pluginName),
					pluginType,
					NULL)) == NULL)
			{
				// Release lock
				PyGILState_Release(state);

				Logger::getLogger()->fatal("plugin_handle: plugin_init(): "
							"failed to create Python module "
							"object, plugin '%s', type '%s'",
							pluginName,
							pluginType.c_str());

				return NULL;
			}


			// Add module to the list of loaded modules
			ret = pythonModules->insert(pair<string, PythonModule*>
						(string(pluginName), newModule));
		}

		// Check result
		if (!pythonModules || ret.second == false)
		{
			Logger::getLogger()->fatal("%s:%d: python module "
						"not added to the map "
						"of loaded plugins, "
						"pModule=%p, plugin '%s', type '%s', aborting.",
						__FUNCTION__,
						__LINE__,
						pModule,
						pluginName,
						pluginType.c_str());

			// Cleanup
			Py_CLEAR(pModule);
			pModule = NULL;

			delete newModule;
			newModule = NULL;
		}
		else
		{
			Logger::getLogger()->debug("%s:%d: python module "
						"successfully loaded, "
						"pModule=%p, plugin '%s', type '%s'",
						__FUNCTION__,
						__LINE__,
						pModule,
						pluginName,
						pluginType.c_str());
		}
	}

	// Release locks
	PyGILState_Release(state);

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
	ret = string(json_dumps(pReturn));

	// Remove objects
	Py_CLEAR(pReturn);

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

	// Get Python object
	ret = string(json_dumps(pReturn));

	// REmove objects
	Py_CLEAR(pReturn);

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
	PyObject *evalData = json_loads(assetValues.c_str());

	vector<PyObject*> removeObjects;
	// Replace content of some known string data:
	// DPImage
	substituteObjects(evalData, removeObjects);

	// Call plugin_eval
	PyObject* pReturn = PyObject_CallFunction(pFunc,
						  "OO",
						  handle,
						  evalData);

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

	// REmove objects
	Py_CLEAR(evalData);
	Py_CLEAR(pReturn);

	// Remove any allocated object in substituteObjects()
	for (auto it = removeObjects.begin();
		  it != removeObjects.end();
		  ++it)
	{
		Py_CLEAR(*it);
	}
	removeObjects.clear();

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
		PyGILState_Release(state);
		return;
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

	// Create Python object from string
	PyObject *config_dict = json_loads(config.c_str());

	// Call Python method passing the Python object
	PyObject* pReturn = PyObject_CallFunction(pFunc,
						  "OO",
						  handle,
						  config_dict);

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
		return ret;
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

	// Transform triggerReason into a Python object
	PyObject *reason = json_loads(triggerReason.c_str());

	// Call Python method passing an object and the data ac C string bu
	// triggerReason as a Python object
	PyObject* pReturn = PyObject_CallFunction(pFunc,
						  "OssOs",
						  handle,
						  deliveryName.c_str(),
						  notificationName.c_str(),
						  reason,
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

	// Remove objects
	Py_CLEAR(reason);
	Py_CLEAR(pReturn);

	PyGILState_Release(state);

	return ret;
}

/**
 * Substitute value for a second level dict in the Pythin object
 * if DPImage string is found
 *
 *  {
 *  	"TC1" : {
 *  		"width" : 256,
 *  		"height" : 256,
 *  		"depth" : 24,
 *  		"img" : "__DPIMAGE:2,2,24_AAAAAAAACAAACAAA"
 *  	},
 *  	"timestamp_TC1" : 1643293555.389629
 *  	}
 *
 *  	"img" string value will be substituted by
 *  	PyArray_SimpleNewFromData(...) data
 */
bool substituteObjects(PyObject *data, vector<PyObject*> &removeObjects)
{

	PyObject *dKey, *dValue;
	Py_ssize_t dPos = 0;

	// Fetch all Datapoints in 'reading' dict
	// dKey and dValue are borrowed references
	while (PyDict_Next(data, &dPos, &dKey, &dValue))
	{
		if (PyDict_Check(dValue))
		{
			PyObject *iKey, *iValue;
			Py_ssize_t iPos = 0;
			while (PyDict_Next(dValue, &iPos, &iKey, &iValue))
			{
				if (PyUnicode_Check(iValue))
				{
					string str = PyUnicode_AsUTF8(iValue);
					string key = PyUnicode_AsUTF8(iKey);
					if (str[0] == '_' && str[1] == '_')
					{
						size_t pos = str.find_first_of(':');
						if (str.compare(2, 7, "DPIMAGE") == 0)
						{
							PyObject *newImage = NULL;
							DPImage *image = new Base64DPImage(str.substr(pos + 1));

							Logger::getLogger()->debug("Inner key '%s' will be "
										"substituted with a DPImage of %dx%d@%d",
										key.c_str(),
										image->getHeight(),
										image->getWidth(),
										image->getDepth());

							// Initialise Nunpy array
							import_array();

							if (image->getDepth() == 24)
							{
								npy_intp dim[3];
								dim[0] = image->getHeight();
								dim[1] = image->getWidth();
								dim[2] = 3;
								enum NPY_TYPES type = NPY_UBYTE;

								// Create Python array wrapper around image data
								newImage = PyArray_SimpleNewFromData(3,
												dim,
												type,
												image->getData());
							}
							else
							{
								npy_intp dim[2];
								dim[0] = image->getHeight();
								dim[1] = image->getWidth();
								enum NPY_TYPES type;
								bool createImage = true;
								switch (image->getDepth())
								{
									case 8:
										type = NPY_UBYTE;
											break;
									case 16:
										type = NPY_UINT16;
										break;
									case 32:
										type = NPY_UINT32;
										break;
									case 64:
										type = NPY_UINT64;
										break;
									default:
										createImage = false;
										break;
								}
								if (createImage)
								{
									// Create Python array wrapper around image data
									newImage = PyArray_SimpleNewFromData(2,
													dim,
													type,
													image->getData());
								}
							}
							if (newImage)
							{
								// Replace value
								PyDict_SetItem(dValue, iKey, newImage);

								// Add object to remove vector
								removeObjects.push_back(newImage);
							}
	
							// Delete DPImage object
							delete(image);
						}
						if (str.compare(2, 10, "DATABUFFER") == 0)
						{
							PyObject *newImage = NULL;
							DataBuffer *dbuf = new Base64DataBuffer(str.substr(pos + 1));
							npy_intp dim = dbuf->getItemCount();
							enum NPY_TYPES type;
							bool createImage = true;
							switch (dbuf->getItemSize())
							{
								case 1:
									type = NPY_UBYTE;
									break;
								case 2:
									type = NPY_UINT16;
									break;
								case 4:
									type = NPY_UINT32;
									break;
								case 8:
									type = NPY_UINT64;
									break;
								default:
									createImage = false;
									break;
							}
							// Initialise Nunpy array
							import_array();

							if (createImage)
							{
								// Create Python array wrapper around image data
								newImage = PyArray_SimpleNewFromData(1, &dim, type, dbuf->getData());
								if (newImage)
								{
									// Replace value
									PyDict_SetItem(dValue, iKey, newImage);

									// Add object to remove vector
									removeObjects.push_back(newImage);
								}
							}
	
							// Delete Databiffer object
							delete(dbuf);
						}
					}
				}
			}
		}
	}

	return true;
}
}; // End of extern C
