#ifndef _PYTHON_PLUGIN_BASE_INTERFACE_H
#define _PYTHON_PLUGIN_BASE_INTERFACE_H
/*
 * Fledge common plugin interface
 *
 * Copyright (c) 2019 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Massimiliano Pinto, Amandeep Singh Arora
 */

#include <plugin_manager.h>

#define SHIM_SCRIPT_REL_PATH  "/python/fledge/plugins/common/shim/"
#define SHIM_SCRIPT_POSTFIX "_shim"

using namespace std;

/**
 * This class represents the loaded Python module
 * with interpreter initialisation flag.
 * That flag is checked in PluginInterfaceCleanup
 * before removing Python interpreter.
 */
class PythonModule
{
	public:
		PythonModule(PyObject* module,
			    bool init,
			    string name,
			    string type,
			    PyThreadState* state) :
			m_module(module),
			m_init(init),
			m_name(name),
			m_type(type),
			m_tState(state)
		{
		};

		~PythonModule()
		{
			// Destroy loaded Python module
			Py_CLEAR(m_module);
			m_module = NULL;
		};

		void	setCategoryName(string category)
		{
			m_categoryName = category;
		};

		string&	getCategoryName()
		{
			return m_categoryName;
		};

	public:
		PyObject* m_module;
		bool      m_init;
		string    m_name;
		string    m_type;
		PyThreadState*	m_tState;
		string    m_categoryName;
};

extern "C" {
// This is the map of Python object initialised in each 
// South, Notification, Filter  plugin interfaces
static map<string, PythonModule*> *pythonModules = new map<string, PythonModule*>();
// Map of PLUGIN_HANDLE objects, updated by plugin_init calls
static map<PLUGIN_HANDLE, PythonModule*> *pythonHandles = new map<PLUGIN_HANDLE, PythonModule*>();

// Global variable gPluginName set by PluginInterfaceInit:
// it has a different memory address when set/read by
// PluginInterfaceInit in South, Filter or Notification
// Only used in plugin_info_fn calls
static string gPluginName;

// Common methods to all plugin interfaces
static PLUGIN_INFORMATION *plugin_info_fn();
static PLUGIN_HANDLE plugin_init_fn(ConfigCategory *);
static void plugin_reconfigure_fn(PLUGIN_HANDLE*, const std::string&);
static void plugin_shutdown_fn(PLUGIN_HANDLE);

static void logErrorMessage();
static bool numpyImportError = false;
void setImportParameters(string& shimLayerPath, string& fledgePythonDir);

PyObject* createReadingsList(const vector<Reading *>& readings, bool changeDictKeys = false);

/**
 * Destructor for PythonPluginHandle
 *    - Free up owned references
 *    - Unload python 3.5 interpreter
 *
 * @param plugnName	The Python plugin to cleanup
 */
void PluginInterfaceCleanup(const string& pluginName)
{
	bool removePython = false;

	if (!pythonModules)
	{
		Logger::getLogger()->error("pythonModules map is NULL "
					   "in PluginInterfaceCleanup, plugin '%s'",
					   pluginName.c_str());

		return;
	}

	// Acquire GIL
	PyGILState_STATE state = PyGILState_Ensure();

	// Look for Python module, pluginName is the key
	auto it = pythonModules->find(pluginName);
	if (it != pythonModules->end())
	{
		// Remove Python 3.x environment?
		removePython = it->second->m_init;

		// Remove this element
		pythonModules->erase(it);
	}

	// Look for Python module handle
	for (auto h = pythonHandles->begin();
		  h != pythonHandles->end(); )
	{
		// Compare pluginName with m_name
		if (h->second->m_name.compare(pluginName) == 0)
		{
			// Remove PythonModule object
			if (h->second->m_module)
			{
				Py_CLEAR(h->second->m_module);
				h->second->m_module = NULL;
			}

			// Remove PythonModule
			delete h->second;
			h->second = NULL;

			// Remove this element
			h = pythonHandles->erase(h);
		}
		else
		{
			++h;
		}
	}

	// Remove PythonModule object
	if (it->second &&
	    it->second->m_module)
	{
		Py_CLEAR(it->second->m_module);
		it->second->m_module = NULL;
	}

	// Remove all maps if empty
	if (pythonModules->size() == 0)
	{
		// Remove map object
		delete pythonModules;
	}
	if (pythonHandles->size() == 0)
	{
		// Remove map object
		delete pythonHandles;
	}

	if (removePython)
	{
		Logger::getLogger()->debug("Removing Python interpreter "
					   "started by plugin '%s'",
					   pluginName.c_str());

		// Cleanup Python 3.5
		Py_Finalize();
	}
	else
	{
		PyGILState_Release(state);
	}

	Logger::getLogger()->debug("PluginInterfaceCleanup succesfully "
				   "called for plugin '%s'",
				   pluginName.c_str());
}

/**
 * Returns function pointer that can be invoked to call 'plugin_info'
 * function in python plugin
 */
static void* PluginInterfaceGetInfo()
{
	return (void *) plugin_info_fn;
}

/**
 * Fill PLUGIN_INFORMATION structure from Python object
 *
 * @param pyRetVal      Python 3.5 Object (dict)
 * @return              Pointer to a new PLUGIN_INFORMATION structure
 *                              or NULL in case of errors
 */
static PLUGIN_INFORMATION *Py2C_PluginInfo(PyObject* pyRetVal)
{
	// Create returnable PLUGIN_INFORMATION structure
	PLUGIN_INFORMATION *info = new PLUGIN_INFORMATION;

	// these are borrowed references returned by PyDict_Next
	PyObject *dKey, *dValue;
	Py_ssize_t dPos = 0;

	// dKey and dValue are borrowed references
	while (PyDict_Next(pyRetVal, &dPos, &dKey, &dValue))
	{
		const char* ckey = PyUnicode_AsUTF8(dKey);
		const char* cval = PyUnicode_AsUTF8(dValue);

		char *valStr = new char [string(cval).length()+1];
		std::strcpy (valStr, cval);

		if(!strcmp(ckey, "name"))
		{
			info->name = valStr;
		}
		else if(!strcmp(ckey, "version"))
		{
			info->version = valStr;
		}
		else if(!strcmp(ckey, "mode"))
		{
			info->options = 0;
			if (!strcmp(valStr, "async"))
			{
				info->options |= SP_ASYNC;
			}
			free(valStr);
		}
		else if(!strcmp(ckey, "type"))
		{
			info->type = valStr;
		}
		else if(!strcmp(ckey, "interface"))
		{
			info->interface = valStr;
		}
		else if(!strcmp(ckey, "config"))
		{
			info->config = valStr;
		}
	}

	return info;
}

/**
 * Function to invoke 'plugin_info' function in python plugin
 */
static PLUGIN_INFORMATION *plugin_info_fn()
{
	if (!pythonModules)
	{
		Logger::getLogger()->error("pythonModules map is NULL "
					   "in plugin_info_fn, plugin '%s'",
					   gPluginName.c_str());
		return NULL;
	}

	// Look for Python module for gPluginName key
	auto it = pythonModules->find(gPluginName);
	if (it == pythonModules->end() ||
	    !it->second ||
	    !it->second->m_module)
	{
		Logger::getLogger()->fatal("plugin_handle: plugin_info(): "
					   "pModule is NULL for plugin '%s'",
					   gPluginName.c_str());
		return NULL;
	}
	PyObject* pFunc; 
	PyGILState_STATE state = PyGILState_Ensure();

	// Fetch required method in loaded object
	pFunc = PyObject_GetAttrString(it->second->m_module, "plugin_info");
	if (!pFunc)
	{
		Logger::getLogger()->fatal("Cannot find method 'plugin_info' "
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

		Logger::getLogger()->fatal("Cannot call method 'plugin_info' "
					   "in loaded python module '%s'",
					   gPluginName.c_str());
		Py_CLEAR(pFunc);

		PyGILState_Release(state);
		return NULL;
	}

	// Call Python method passing an object
	PyObject* pReturn = PyObject_CallFunction(pFunc, NULL);

	Py_CLEAR(pFunc);

	PLUGIN_INFORMATION *info = NULL;

	// Handle returned data
	if (!pReturn)
	{
		Logger::getLogger()->error("Called python script method 'plugin_info' "
					    ": error while getting result object, plugin '%s'",
					   gPluginName.c_str());
		logErrorMessage();
		info = NULL;
	}
	else
	{
		// Parse plugin information
		info = Py2C_PluginInfo(pReturn);

		// Remove pReturn object
		Py_CLEAR(pReturn);
	}

	if (info)
	{
		// bump interface version to atleast 2.x so that we are able to handle
		// list of readings from python plugins in plugin_poll
		if (info->interface[0] =='1' &&
		    info->interface[1] == '.')
		{
			Logger::getLogger()->info("plugin_handle: plugin_info(): "
						   "Updating interface version "
						   "from '%s' to '2.0.0', plugin '%s'",
						   info->interface,
						   gPluginName.c_str());
			delete info->interface;
			char *valStr = new char[6];
			std::strcpy(valStr, "2.0.0");
			info->interface = valStr;
		}

		Logger::getLogger()->info("plugin_handle: plugin_info(): info={name=%s, "
					   "version=%s, options=%d, type=%s, interface=%s, config=%s}",
					   info->name,
					   info->version,
					   info->options,
					   info->type,
					   info->interface,
					   info->config);
	}

	PyGILState_Release(state);

	return info;
}

/**
 * Function to invoke 'plugin_init' function in python plugin
 *
 * @param    config	ConfigCategory configuration object
 * @retun		PLUGIN_HANDLE object
 */
static PLUGIN_HANDLE plugin_init_fn(ConfigCategory *config)
{
	// Get plugin name
	string pName = config->getValue("plugin");

	if (!pythonModules)
	{
		Logger::getLogger()->error("pythonModules map is NULL "
					   "in plugin_init_fn, plugin '%s'",
					   pName.c_str());
		return NULL;
	}

	Logger::getLogger()->debug("plugin_handle: plugin_init(): "
				   "config->itemsToJSON()='%s'",
				   config->itemsToJSON().c_str());

	bool loadModule = false;
	bool reloadModule = false;
	bool pythonInitState = false;
	string loadPluginType;

	PythonModule* module = NULL;
	PyThreadState* newInterp = NULL;

	// Check wether plugin pName has been already loaded
	for (auto h = pythonHandles->begin();
		  h != pythonHandles->end();
		  ++h)
	{
		if (h->second->m_name.compare(pName) == 0)
		{
			Logger::getLogger()->debug("%s_plugin_init_fn: already loaded "
						   "a plugin with name '%s'. Loading a new "
						   "Python module using a new interpreter.",
						   h->second->m_type.c_str(),
						   pName.c_str());

			// Set Python library loaded state
			pythonInitState = h->second->m_init;

			// Set plugin type
			loadPluginType = h->second->m_type;

			// Set load indicator
			loadModule = true;
		}
	}

	if (!loadModule)
	{

		// Plugin name not previously loaded: check current Python module
		// pName is the key
		auto it = pythonModules->find(pName);
		if (it == pythonModules->end())
		{
			Logger::getLogger()->debug("plugin_handle: plugin_init(): "
						   "pModule nof found for plugin '%s': "
						   "import Python module using a new interpreter.",
						   pName.c_str());

			// Set plugin type
			PluginManager* pMgr = PluginManager::getInstance();	
			PLUGIN_HANDLE tmp = pMgr->findPluginByName(pName);
			if (tmp)
			{
				PLUGIN_INFORMATION* pInfo = pMgr->getInfo(tmp);
				if (pInfo)
				{
					loadPluginType = string(pInfo->type);
				}
			}

			// Set reload indicator
			reloadModule = true;
		}
		else
		{
			if (it->second && it->second->m_module)
			{
				// Just use current loaded module: no load or re-load action
				module = it->second;

				// Set Python library loaded state
				pythonInitState = it->second->m_init;
			}
			else
			{
				Logger::getLogger()->fatal("plugin_handle: plugin_init(): "
							   "found pModule is NULL for plugin '%s': ",
							   pName.c_str());
				return NULL;
			}
		}
	}

	// Acquire GIL
	PyGILState_STATE state = PyGILState_Ensure();

	// Import Python module using a new interpreter
	if (loadModule || reloadModule)
	{
		// Start a new interpreter
		newInterp = Py_NewInterpreter();
		if (!newInterp)
		{
			Logger::getLogger()->fatal("plugin_handle: plugin_init() "
						   "Py_NewInterpreter failure "
						   "for for plugin '%s': ",
						   pName.c_str());
			logErrorMessage();

			PyGILState_Release(state);
			return NULL;
		}

		string shimLayerPath;
		string fledgePythonDir;
	
		// Python 3.x set parameters for import
		setImportParameters(shimLayerPath, fledgePythonDir);

		string name;
		int argc = 2;

		// Set Python path for embedded Python 3.x
		// Get current sys.path - borrowed reference
		PyObject* sysPath = PySys_GetObject((char *)"path");
		PyList_Append(sysPath, PyUnicode_FromString((char *) fledgePythonDir.c_str()));
		PyList_Append(sysPath, PyUnicode_FromString((char *) shimLayerPath.c_str()));

		// For notificationRUle/Delivery plugins we need another import parameter
		if (loadPluginType.find("notification") != string::npos)
		{
			name = "notification" + string(SHIM_SCRIPT_POSTFIX);
			argc++;
		}
		else
		{
			name = loadPluginType + string(SHIM_SCRIPT_POSTFIX);
		}

		// Set sys.argv for embedded Python 3.x
		wchar_t* argv[argc];
		argv[0] = Py_DecodeLocale("", NULL);
		argv[1] = Py_DecodeLocale(pName.c_str(), NULL);
		if (argc > 2)
		{
			argv[2] = Py_DecodeLocale(loadPluginType.c_str(), NULL);
		}

		// Set script parameters
		PySys_SetArgv(argc, argv);

		Logger::getLogger()->debug("%s_plugin_init_fn, %sloading plugin '%s', "
					   "using a new interpreter, SHIM file is '%s'",
					   loadPluginType.c_str(),
					   string(reloadModule ? "re-" : "").c_str(), 
					   pName.c_str(),
					   name.c_str());

		// Import Python script
		PyObject *newObj = PyImport_ImportModule(name.c_str());

		// Check result
		if (newObj)
		{
			// Create a new PythonModule
			PythonModule* newModule;
			if ((newModule = new PythonModule(newObj,
							  pythonInitState,
							  pName,
							  loadPluginType,
							  newInterp)) == NULL)
			{
				// Release lock
				PyEval_ReleaseThread(newInterp);

				Logger::getLogger()->fatal("plugin_handle: plugin_init(): "
							   "failed to create Python module "
							   "object, plugin '%s'",
							   pName.c_str());
				return NULL;
			}

			// Set module
			module = newModule;
		}
		else
		{
			logErrorMessage();

			// Release lock
			PyEval_ReleaseThread(newInterp);

			Logger::getLogger()->fatal("plugin_handle: plugin_init(): "
						   "failed to import plugin '%s'",
						   pName.c_str());
			return NULL;
		}
	}

	Logger::getLogger()->debug("%s_plugin_init_fn for '%s', pModule '%p', "
				   "Python interpreter '%p'",
				   loadPluginType.c_str(),
				   module->m_name.c_str(),
				   module->m_module,
				   module->m_tState);

	// Call Python method passing an object
	PyObject* pReturn = PyObject_CallMethod(module->m_module,
						"plugin_init",
						"s",
						config->itemsToJSON().c_str());

	// Handle returned data
	if (!pReturn)
	{
		Logger::getLogger()->error("Called python script method plugin_init : "
					   "error while getting result object, plugin '%s'",
					   pName.c_str());
		logErrorMessage();
	}
	else
	{
		Logger::getLogger()->debug("plugin_handle: plugin_init(): "
					   "got handle from python plugin='%p', *handle %p, plugin '%s'",
					   pReturn,
					   &pReturn,
					   pName.c_str());
	}

	// Add the handle to handles map as key, PythonModule object as value
	std::pair<std::map<PLUGIN_HANDLE, PythonModule*>::iterator, bool> ret;
	if (pythonHandles)
	{
		// Add to handles map the PythonModule object
		ret = pythonHandles->insert(pair<PLUGIN_HANDLE, PythonModule*>
			((PLUGIN_HANDLE)pReturn, module));

		if (ret.second)
		{
			Logger::getLogger()->debug("plugin_handle: plugin_init(): "
						   "handle %p of python plugin '%s' "
						   "added to pythonHandles map",
						   pReturn,
						   pName.c_str());
		}
		else
		{
			Logger::getLogger()->error("plugin_handle: plugin_init(): "
						   "failed to insert handle %p of "
						   "python plugin '%s' to pythonHandles map",
						   pReturn,
						   pName.c_str());

			Py_CLEAR(module->m_module);
			module->m_module = NULL;
			delete module;
			module = NULL;

			Py_CLEAR(pReturn);
			pReturn = NULL;
		}
	}

	// Release locks
	if (newInterp)
	{
		PyEval_ReleaseThread(newInterp);
	}
	else
	{
		PyGILState_Release(state);
	}

	return pReturn ? (PLUGIN_HANDLE) pReturn : NULL;
}

/**
 * Function to invoke 'plugin_reconfigure' function in python plugin
 *
 * @param    handle	The plugin handle from plugin_init_fn
 * @param    config	The new configuration, as string
 */
static void plugin_reconfigure_fn(PLUGIN_HANDLE* handle,
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
		Logger::getLogger()->error("pythonHandles map is NULL "
					   "in plugin_reconfigure, plugin handle '%p'",
					   handle);
		return;
	}

	// Look for Python module for handle key
	auto it = pythonHandles->find(*handle);
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
	PyObject* pFunc;
	lock_guard<mutex> guard(mtx);
	PyGILState_STATE state = PyGILState_Ensure();

	Logger::getLogger()->debug("plugin_handle: plugin_reconfigure(): "
				   "pModule=%p, *handle=%p, plugin '%s'",
				   it->second->m_module,
				   *handle,
				   it->second->m_name.c_str());

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

		Logger::getLogger()->fatal("Cannot call method plugin_reconfigure "
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
						  *handle,
						  config.c_str());

	Py_CLEAR(pFunc);

	// Handle returned data
	if (!pReturn)
	{
		Logger::getLogger()->error("Called python script method plugin_reconfigure "
					   ": error while getting result object, plugin '%s'",
					   it->second->m_name.c_str());
		logErrorMessage();
		//*handle = NULL; // not sure if this should be treated as unrecoverable failure on python plugin side
	}
	else
	{
                // Save PythonModule
		PythonModule* currentModule = it->second;

		Py_CLEAR(*handle);
		*handle = pReturn;

		if (pythonHandles)
		{
			// Remove current handle from the pythonHandles map
			pythonHandles->erase(it);

			// Add the handle to handles map as key, PythonModule object as value
			std::pair<std::map<PLUGIN_HANDLE, PythonModule*>::iterator, bool> ret;
			ret = pythonHandles->insert(pair<PLUGIN_HANDLE, PythonModule*>
				((PLUGIN_HANDLE)*handle, currentModule));

			Logger::getLogger()->debug("plugin_handle: plugin_reconfigure(): "
						   "updated handle %p of python plugin '%s'"
						   " in pythonHandles map",
						   *handle,
						   currentModule->m_name.c_str());
		}
		else
		{
			Logger::getLogger()->error("plugin_handle: plugin_reconfigure(): "
						   "failed to update handle %p of python plugin '%s'"
						   " in pythonHandles map",
						   *handle,
						   currentModule->m_name.c_str());
		}
	}

	PyGILState_Release(state);
}

/**
 * Function to log error message encountered while interfacing with
 * Python runtime
 */
static void logErrorMessage()
{
	PyObject* type;
	PyObject* value;
	PyObject* traceback;

	numpyImportError = false;

	PyErr_Fetch(&type, &value, &traceback);
	PyErr_NormalizeException(&type, &value, &traceback);

	PyObject* str_exc_value = PyObject_Repr(value);
	PyObject* pyExcValueStr = PyUnicode_AsEncodedString(str_exc_value, "utf-8", "Error ~");
	const char* pErrorMessage = value ?
				    PyBytes_AsString(pyExcValueStr) :
				    "no error description.";
	Logger::getLogger()->fatal("logErrorMessage: Error '%s', plugin '%s'",
				   pErrorMessage,
				   gPluginName.c_str());
	
	// Check for numpy/pandas import errors
	const char *err1 = "implement_array_function method already has a docstring";
	const char *err2 = "cannot import name 'check_array_indexer' from 'pandas.core.indexers'";

	numpyImportError = strstr(pErrorMessage, err1) || strstr(pErrorMessage, err2);
	
	std::string fcn = "";
	fcn += "def get_pretty_traceback(exc_type, exc_value, exc_tb):\n";
	fcn += "    import sys, traceback\n";
	fcn += "    lines = []\n"; 
	fcn += "    lines = traceback.format_exception(exc_type, exc_value, exc_tb)\n";
	fcn += "    output = '\\n'.join(lines)\n";
	fcn += "    return output\n";

	PyRun_SimpleString(fcn.c_str());
	PyObject* mod = PyImport_ImportModule("__main__");
	if (mod != NULL) {
		PyObject* method = PyObject_GetAttrString(mod, "get_pretty_traceback");
		if (method != NULL) {
			PyObject* outStr = PyObject_CallObject(method, Py_BuildValue("OOO", type, value, traceback));
			if (outStr != NULL) {
				PyObject* tmp = PyUnicode_AsASCIIString(outStr);
				if (tmp != NULL) {
					std::string pretty = PyBytes_AsString(tmp);
					Logger::getLogger()->fatal("%s", pretty.c_str());
					Logger::getLogger()->printLongString(pretty.c_str());
				}
				Py_CLEAR(tmp);
			}
			Py_CLEAR(outStr);
		}
		Py_CLEAR(method);
	}

	// Reset error
	PyErr_Clear();

	// Remove references
	Py_CLEAR(type);
	Py_CLEAR(value);
	Py_CLEAR(traceback);
	Py_CLEAR(str_exc_value);
	Py_CLEAR(pyExcValueStr);
	Py_CLEAR(mod);
}

/**
 * Function to invoke 'plugin_shutdown' function in python plugin
 *
 * @param    handle	The plugin handle from plugin_init_fn
 */
static void plugin_shutdown_fn(PLUGIN_HANDLE handle)
{
	if (!handle)
	{
		Logger::getLogger()->fatal("plugin_handle: plugin_shutdown_fn: "
					   "handle is NULL");
		return;
	}

	if (!pythonHandles)
	{
		Logger::getLogger()->error("pythonHandles map is NULL "
					   "in plugin_shutdown_fn, plugin handle '%p'",
					   handle);
		return;
	}

	// Look for Python module for handle key
	auto it = pythonHandles->find(handle);
	if (it == pythonHandles->end() ||
	    !it->second ||
	    !it->second->m_module)
	{
		Logger::getLogger()->fatal("plugin_handle: plugin_shutdown_fn: "
					   "pModule is NULL, plugin handle '%p'",
					   handle);
		return;
	}

	if (! Py_IsInitialized()) {

		Logger::getLogger()->debug("%s - Python environment not initialized, exiting from the function ", __FUNCTION__);
		return;
	}

	PyObject* pFunc; 
	PyGILState_STATE state = PyGILState_Ensure();

	// Fetch required method in loaded object
	pFunc = PyObject_GetAttrString(it->second->m_module, "plugin_shutdown");
	if (!pFunc)
	{
		Logger::getLogger()->fatal("Cannot find method 'plugin_shutdown' "
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

		Logger::getLogger()->fatal("Cannot call method 'plugin_shutdown' "
					   "in loaded python module '%s'",
					   it->second->m_name.c_str());
		Py_CLEAR(pFunc);

		PyGILState_Release(state);
		return;
	}

	// Call Python method passing an object
	PyObject* pReturn = PyObject_CallFunction(pFunc,
						  "O",
						  handle);

	Py_CLEAR(pFunc);

        // Handle return
	if (!pReturn)
	{       
		Logger::getLogger()->error("Called python script method plugin_shutdown "
					   ": error while getting result object, plugin '%s'",
					   it->second->m_name.c_str());
		logErrorMessage();
	}

	if (it->second->m_tState)
	{
		// Switch to Interpreter thread
		PyThreadState* swapState = PyThreadState_Swap(it->second->m_tState);

		// Remove Python module
		Py_CLEAR(it->second->m_module);
		it->second->m_module = NULL;

		// Stop Interpreter thread
		Py_EndInterpreter(it->second->m_tState);

		Logger::getLogger()->debug("plugin_shutdown_fn: Py_EndInterpreter of '%p' "
					   "for plugin '%s'",
					   it->second->m_tState,
					   it->second->m_name.c_str());
		// Return to main thread
		PyThreadState_Swap(swapState);

		// Set pointer to null
		it->second->m_tState = NULL;
	}
	else
	{
		// Remove Python module
		Py_CLEAR(it->second->m_module);
		it->second->m_module = NULL;
	}

	PythonModule* module = it->second;
	string pName = it->second->m_name;

	// Remove item
	pythonHandles->erase(it);

	// Look for Python module, pName is the key
	auto m = pythonModules->find(pName);
	if (m != pythonModules->end())
	{
		// Remove this element
		pythonModules->erase(m);
	}

	// Release module object
	delete module;
	module = NULL;

	// Release GIL
	PyGILState_Release(state);

	Logger::getLogger()->debug("plugin_shutdown_fn succesfully "
				   "called for plugin '%s'",
				   pName.c_str());
}

/**
 * Fill input string parameters with needed values for Python import
 *
 * @param shimLayerPath		Full path of Python shim layer file
 * @param fledgePythonDir	Location of Python module files under FLEDGE_ROOT
 */
void setImportParameters(string&shimLayerPath, string& fledgePythonDir)
{
	// Get FLEDGE_ROOT dir
	string fledgeRootDir(getenv("FLEDGE_ROOT"));
	string path = fledgeRootDir + SHIM_SCRIPT_REL_PATH;
	fledgePythonDir = fledgeRootDir + "/python";

	// Python 3.x script name
	std::size_t found = path.find_last_of("/");
	shimLayerPath = path.substr(0, found);
}

};
#endif
