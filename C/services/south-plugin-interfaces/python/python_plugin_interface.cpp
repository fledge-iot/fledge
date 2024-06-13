/*
 * Fledge south plugin interface related
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Amandeep Singh Arora
 */

#include <logger.h>
#include <config_category.h>
#include <reading_set.h>
#include <mutex>
#include <south_plugin.h>
#include <pyruntime.h>
#include <Python.h>
#include <python_plugin_common_interface.h>
#include <pythonreadingset.h>

#define SHIM_SCRIPT_NAME "south_shim"

using namespace std;

extern "C" {

extern PLUGIN_INFORMATION *plugin_info_fn();
extern PLUGIN_HANDLE plugin_init_fn(ConfigCategory *);
extern void plugin_reconfigure_fn(PLUGIN_HANDLE*, const std::string&);
extern void plugin_shutdown_fn(PLUGIN_HANDLE);
extern void logErrorMessage();
extern PLUGIN_INFORMATION *Py2C_PluginInfo(PyObject *);

// South plugin entry points
std::vector<Reading *>* plugin_poll_fn(PLUGIN_HANDLE);
void plugin_start_fn(PLUGIN_HANDLE handle);
void plugin_register_ingest_fn(PLUGIN_HANDLE handle,INGEST_CB2 cb,void * data);
bool plugin_write_fn(PLUGIN_HANDLE handle, const std::string& name, const std::string& value);
bool plugin_operation_fn(PLUGIN_HANDLE handle, string operation, int parameterCount, PLUGIN_PARAMETER *parameters[]);


/**
 * Constructor for PythonPluginHandle
 */
void *PluginInterfaceInit(const char *pluginName, const char * pluginPathName)
{
    bool initialisePython = false;

    // Set plugin name, also for methods in common-plugin-interfaces/python
    gPluginName = pluginName;

    string fledgePythonDir;
    
    string fledgeRootDir(getenv("FLEDGE_ROOT"));
	fledgePythonDir = fledgeRootDir + "/python";
    
    string southRootPath = fledgePythonDir + string(R"(/fledge/plugins/south/)") + string(pluginName);
    Logger::getLogger()->info("%s:%d:, southRootPath=%s", __FUNCTION__, __LINE__, southRootPath.c_str());
    
    // Embedded Python 3.5 program name
    wchar_t *programName = Py_DecodeLocale(pluginName, NULL);
    Py_SetProgramName(programName);
    PyMem_RawFree(programName);

    PythonRuntime::getPythonRuntime();
    
    // Acquire GIL
    PyGILState_STATE state = PyGILState_Ensure();

    Logger::getLogger()->info("SouthPlugin %s:%d: "
                   "southRootPath=%s, fledgePythonDir=%s, plugin '%s'",
                   __FUNCTION__,
                   __LINE__,
                   southRootPath.c_str(),
                   fledgePythonDir.c_str(),
                   pluginName);
    
    // Set Python path for embedded Python 3.x
    // Get current sys.path - borrowed reference
    PyObject* sysPath = PySys_GetObject((char *)"path");
    PyList_Append(sysPath, PyUnicode_FromString((char *) southRootPath.c_str()));
    PyList_Append(sysPath, PyUnicode_FromString((char *) fledgePythonDir.c_str()));

    // Set sys.argv for embedded Python 3.5
	int argc = 2;
	wchar_t* argv[2];
	argv[0] = Py_DecodeLocale("", NULL);
	argv[1] = Py_DecodeLocale(pluginName, NULL);
	PySys_SetArgv(argc, argv);

    // 2) Import Python script
    PyObject *pModule = PyImport_ImportModule(pluginName);

    // Check whether the Python module has been imported
    if (!pModule)
    {
        // Failure
        if (PyErr_Occurred())
        {
            logErrorMessage();
        }
        Logger::getLogger()->fatal("PluginInterfaceInit: cannot import Python 3.5 script "
                       "'%s' from '%s' : plugin '%s'",
                       pluginName, southRootPath.c_str(),
                       pluginName);
    }
    else
    {
        std::pair<std::map<string, PythonModule*>::iterator, bool> ret;
        if (pythonModules)
        {
            // Add element
            ret = pythonModules->insert(pair<string, PythonModule*>
                (string(pluginName), new PythonModule(pModule,
                                      initialisePython,
                                      string(pluginName),
                                      PLUGIN_TYPE_SOUTH,
                                      // New Python interpteter not set
                                      NULL)));
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
            Py_CLEAR(pModule);
            return NULL;
        }
        else
        {
            Logger::getLogger()->debug("%s:%d: python module loaded successfully, pModule=%p, plugin '%s'",
                           __FUNCTION__,
                           __LINE__,
                           pModule,
                           pluginName);
        }
    }

    // Release GIL
    PyGILState_Release(state);

    return pModule;
}

/**
 * Function to invoke 'plugin_write' function in python plugin
 *
 * @param    handle		Plugin handle from plugin_init_fn
 * @param    name		Name of parameter to write
 * @param    value		Value to be written to that parameter
 */
bool plugin_write_fn(PLUGIN_HANDLE handle, const std::string& name, const std::string& value)
{
	bool rv = false;

	if (!handle)
	{
		Logger::getLogger()->fatal("plugin_handle: plugin_write(): "
					   "handle is NULL");
		return rv;
	}

	if (!pythonHandles)
	{
		Logger::getLogger()->error("pythonHandles map is NULL "
					   "in plugin_write, plugin handle '%p'",
					   handle);
		return rv;
	}

	// Look for Python module for handle key
	auto it = pythonHandles->find(handle);
	if (it == pythonHandles->end() ||
		!it->second ||
		!it->second->m_module)
	{
		Logger::getLogger()->fatal("plugin_handle: plugin_write(): "
					   "pModule is NULL, plugin handle '%p'",
					   handle);
		return rv;
	}

	std::mutex mtx;
	PyObject* pFunc;
	lock_guard<mutex> guard(mtx);
	PyGILState_STATE state = PyGILState_Ensure();

	Logger::getLogger()->debug("plugin_handle: plugin_write(): "
				   "pModule=%p, handle=%p, plugin '%s'",
				   it->second->m_module,
				   handle,
				   it->second->m_name.c_str());

	// Fetch required method in loaded object
	pFunc = PyObject_GetAttrString(it->second->m_module, "plugin_write");
	if (!pFunc)
	{
		Logger::getLogger()->fatal("Cannot find method 'plugin_write' "
					   "in loaded python module '%s'",
					   it->second->m_name.c_str());

		PyGILState_Release(state);
		return rv;
	}

	if (!PyCallable_Check(pFunc))
	{
		// Failure
		if (PyErr_Occurred())
		{
			logErrorMessage();
		}

		Logger::getLogger()->fatal("Cannot call method plugin_write "
					   "in loaded python module '%s'",
					   it->second->m_name.c_str());
		Py_CLEAR(pFunc);

		PyGILState_Release(state);
		return rv;
	}

	Logger::getLogger()->debug("plugin_write with name=%s, value=%s", name.c_str(), value.c_str());

	// Call Python method passing an object and 2 C-style strings
	PyObject* pReturn = PyObject_CallFunction(pFunc,
						  "Oss",
						  handle, name.c_str(), value.c_str());

	Py_CLEAR(pFunc);

	// Handle return
	if (!pReturn)
	{
		Logger::getLogger()->error("Called python script method plugin_write : "
					   "error while getting result object, plugin '%s'",
					   it->second->m_name.c_str());
		logErrorMessage();
	}
	else
	{
		if (PyBool_Check(pReturn))
		{
			rv = PyObject_IsTrue(pReturn);
			Logger::getLogger()->info("plugin_write() returned %s", rv?"TRUE":"FALSE");
		}
		else
		{
			Logger::getLogger()->error("plugin_handle: plugin_write(): "
									"got result object '%p' of unexpected type %s, plugin '%s'",
									pReturn, pReturn->ob_type->tp_name,
									it->second->m_name.c_str());
		}
		Py_CLEAR(pReturn);
	}
	PyGILState_Release(state);

	return rv;
}

/**
 * Function to invoke 'plugin_operation' function in python plugin
 *
 * @param    handle			Plugin handle from plugin_init_fn
 * @param    operation		Name of operation
 * @param    parameterCount	Number of parameters in Parameter list
 * @param    parameters		Parameter list
 */
bool plugin_operation_fn(PLUGIN_HANDLE handle, string operation, int parameterCount, PLUGIN_PARAMETER *parameters[])
{
	bool rv = false;
	if (!handle)
	{
		Logger::getLogger()->fatal("plugin_handle: plugin_operation(): "
					   "handle is NULL");
		return rv;
	}

	if (!pythonHandles)
	{
		Logger::getLogger()->error("pythonHandles map is NULL "
					   "in plugin_operation, plugin handle '%p'",
					   handle);
		return rv;
	}

	// Look for Python module for handle key
	auto it = pythonHandles->find(handle);
	if (it == pythonHandles->end() ||
		!it->second ||
		!it->second->m_module)
	{
		Logger::getLogger()->fatal("plugin_handle: plugin_operation(): "
					   "pModule is NULL, plugin handle '%p'",
					   handle);
		return rv;
	}

	std::mutex mtx;
	PyObject* pFunc;
	lock_guard<mutex> guard(mtx);
	PyGILState_STATE state = PyGILState_Ensure();

	Logger::getLogger()->debug("plugin_handle: plugin_operation(): "
				   "pModule=%p, *handle=%p, plugin '%s'",
				   it->second->m_module,
				   handle,
				   it->second->m_name.c_str());

	// Fetch required method in loaded object
	pFunc = PyObject_GetAttrString(it->second->m_module, "plugin_operation");
	if (!pFunc)
	{
		Logger::getLogger()->fatal("Cannot find method 'plugin_operation' "
					   "in loaded python module '%s'",
					   it->second->m_name.c_str());

		PyGILState_Release(state);
		return rv;
	}

	if (!PyCallable_Check(pFunc))
	{
		// Failure
		if (PyErr_Occurred())
		{
			logErrorMessage();
		}

		Logger::getLogger()->fatal("Cannot call method plugin_operation "
					   "in loaded python module '%s'",
					   it->second->m_name.c_str());
		Py_CLEAR(pFunc);

		PyGILState_Release(state);
		return rv;
	}

	Logger::getLogger()->debug("plugin_operation with operation=%s, parameterCount=%d", operation.c_str(), parameterCount);

	PyObject *paramsList = PyList_New(parameterCount);
	for (int i=0; i<parameterCount; i++)
	{
		PyList_SetItem(paramsList, i, Py_BuildValue("(ss)", parameters[i]->name.c_str(), parameters[i]->value.c_str()) );
	}
	
	// Call Python method passing an object and 2 C-style strings
	PyObject* pReturn = PyObject_CallFunction(pFunc,
						  "OsO",
						  handle, operation.c_str(), paramsList);

	Py_CLEAR(pFunc);
	Py_CLEAR(paramsList);

	// Handle return
	if (!pReturn)
	{
		Logger::getLogger()->error("Called python script method plugin_operation : "
					   "error while getting result object, plugin '%s'",
					   it->second->m_name.c_str());
		logErrorMessage();
	}
	else
	{
		if (PyBool_Check(pReturn))
		{
			rv = PyObject_IsTrue(pReturn);
			Logger::getLogger()->info("plugin_operation() returned %s", rv?"TRUE":"FALSE");
		}
		else
		{
			Logger::getLogger()->error("plugin_handle: plugin_operation(): "
									"got result object '%p' of unexpected type %s, plugin '%s'",
									pReturn, pReturn->ob_type->tp_name,
									it->second->m_name.c_str());
		}
		Py_CLEAR(pReturn);
	}
	PyGILState_Release(state);

	return rv;
}

/**
 * Returns function pointer that can be invoked to call '_sym' function
 * in python plugin
 */
void* PluginInterfaceResolveSymbol(const char *_sym, const string& name)
{
	string sym(_sym);
	if (!sym.compare("plugin_info"))
		return (void *) plugin_info_fn;
	else if (!sym.compare("plugin_init"))
		return (void *) plugin_init_fn;
	else if (!sym.compare("plugin_poll"))
		return (void *) plugin_poll_fn;
	else if (!sym.compare("plugin_shutdown"))
		return (void *) plugin_shutdown_fn;
	else if (!sym.compare("plugin_reconfigure"))
		return (void *) plugin_reconfigure_fn;
	else if (!sym.compare("plugin_start"))
		return (void *) plugin_start_fn;
	else if (!sym.compare("plugin_register_ingest"))
		return (void *) plugin_register_ingest_fn;
	else if (!sym.compare("plugin_write"))
		return (void *) plugin_write_fn;
	else if (!sym.compare("plugin_operation"))
		return (void *) plugin_operation_fn;
	else
	{
		Logger::getLogger()->fatal("PluginInterfaceResolveSymbol can not find symbol '%s' "
					   "in the South Python plugin interface library, loaded plugin '%s'",
					   _sym,
					   name.c_str());
		return NULL;
	}
}

/**
 * Function to invoke 'plugin_poll' function in python plugin
 *
 * @param    handle	Plugin handle from plugin_init_fn
 * @return		Vector of Reading data
 */
std::vector<Reading *>* plugin_poll_fn(PLUGIN_HANDLE handle)
{
	if (!handle)
	{
		Logger::getLogger()->fatal("plugin_handle: plugin_poll_fn: "
					   "handle is NULL");
		return NULL;
	}

	if (!pythonHandles)
	{
		Logger::getLogger()->error("pythonModules map is NULL "
					   "in plugin_poll_fn, handle '%p'",
					   handle);
		 return NULL;
	}

        // Look for Python module for handle key
        auto it = pythonHandles->find(handle);
        if (it == pythonHandles->end() ||
            !it->second ||
            !it->second->m_module)
        {
                Logger::getLogger()->fatal("plugin_handle: plugin_poll(): "
                                           "pModule is NULL, plugin handle '%p'",
                                           handle);
                return NULL;
        }

	std::mutex mtx;
	PyObject* pFunc;
	lock_guard<mutex> guard(mtx);
	PyGILState_STATE state = PyGILState_Ensure();
	
	// Fetch required method in loaded object
	pFunc = PyObject_GetAttrString(it->second->m_module, "plugin_poll");
	if (!pFunc)
	{
		Logger::getLogger()->fatal("Cannot find 'plugin_poll' method "
					   "in loaded python module '%s'",
					   it->second->m_name.c_str());
		PyGILState_Release(state);
		return NULL;
	}

	if (!pFunc || !PyCallable_Check(pFunc))
	{
		// Failure
		if (PyErr_Occurred())
		{
			logErrorMessage();
		}

		Logger::getLogger()->fatal("Cannot call method 'plugin_poll' "
					   "in loaded python module '%s'",
					    it->second->m_name.c_str());
		Py_CLEAR(pFunc);

		PyGILState_Release(state);
		return NULL;
	}

	// Call Python method passing an object
	PyObject* pReturn = PyObject_CallFunction(pFunc,
						  "O",
						  handle);

	Py_CLEAR(pFunc);

	// Handle returned data
	if (!pReturn)
	{
		// Errors while getting result object
		Logger::getLogger()->error("Called python script method 'plugin_poll' : "
					   "error while getting result object, plugin '%s'",
					    it->second->m_name.c_str());
		logErrorMessage();

		PyGILState_Release(state);
		return NULL;
	}
	else
	{
			// Get reading data
		PythonReadingSet *pyReadingSet = NULL;

		// Valid ReadingSet would be in the form of python dict or list
		if (PyList_Check(pReturn) || PyDict_Check(pReturn))
		{
			try {
				pyReadingSet = new PythonReadingSet(pReturn);
			} catch (std::exception e) {
				Logger::getLogger()->warn("Failed to create a Python ReadingSet from the data returned by the south plugin poll routine, %s", e.what());
				pyReadingSet = NULL;
			}
		}
			
		// Remove pReturn object
		Py_CLEAR(pReturn);

		PyGILState_Release(state);

		if (pyReadingSet)
		{
			std::vector<Reading *> *vec2 = pyReadingSet->moveAllReadings();
			delete pyReadingSet;
			return vec2;
		}
		else
		{
			return NULL;
		}
	}
}
	
/**
 * Function to invoke 'plugin_start' function in python plugin
 *
 * @param    handle     Plugin handle from plugin_init_fn
 */
void plugin_start_fn(PLUGIN_HANDLE handle)
{
	if (!handle)
	{
		Logger::getLogger()->fatal("plugin_handle: plugin_start_fn: "
					   "handle is NULL");
		return;
	}

	if (!pythonHandles)
	{
		Logger::getLogger()->error("pythonModules map is NULL "
					   "in plugin_start_fn, handle '%p'",
					   handle);
		 return;
	}

        // Look for Python module for handle key
        auto it = pythonHandles->find(handle);
        if (it == pythonHandles->end() ||
            !it->second ||
            !it->second->m_module)
        {
                Logger::getLogger()->fatal("plugin_handle: plugin_start(): "
                                           "pModule is NULL, plugin handle '%p'",
                                           handle);
                return;
        }

	PyObject* pFunc;
	PyGILState_STATE state = PyGILState_Ensure();
	
	// Fetch required method in loaded object
	pFunc = PyObject_GetAttrString(it->second->m_module, "plugin_start");
	if (!pFunc)
	{
		Logger::getLogger()->warn("Cannot find 'plugin_start' method "
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

		Logger::getLogger()->warn("Cannot call method 'plugin_start' "
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
		Logger::getLogger()->error("Called python script method plugin_start : "
					   "error while getting result object, plugin '%s'",
					   it->second->m_name.c_str());
		logErrorMessage();
	}
	PyGILState_Release(state);
}


/**
 * Function to invoke 'plugin_register_ingest' function in python plugin
 *
 * @param    handle     Plugin handle from plugin_init_fn
 * @param    cb		Ingest routine to call
 * @param    data	Data to pass to Ingest routine
 */
void plugin_register_ingest_fn(PLUGIN_HANDLE handle,
				INGEST_CB2 cb,
				void *data)
{
	if (!handle)
	{
		Logger::getLogger()->fatal("plugin_handle: plugin_register_ingest_fn: "
					   "handle is NULL");
		return;
	}

	if (!pythonHandles)
	{
		Logger::getLogger()->error("pythonModules map is NULL "
					   "in plugin_register_ingest_fn, handle '%p'",
					   handle);
		 return;
	}

        // Look for Python module for handle key
        auto it = pythonHandles->find(handle);
        if (it == pythonHandles->end() ||
            !it->second ||
            !it->second->m_module)
        {
                Logger::getLogger()->fatal("plugin_handle: plugin_register_ingest(): "
                                           "pModule is NULL, plugin handle '%p'",
                                           handle);
                return;
        }

	PyObject* pFunc;
	PyGILState_STATE state = PyGILState_Ensure();
	
	// Fetch required method in loaded object
	pFunc = PyObject_GetAttrString(it->second->m_module, "plugin_register_ingest");
	if (!pFunc)
	{
		Logger::getLogger()->warn("Cannot find 'plugin_register_ingest' "
					   "method in loaded python module '%s'",
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

		Logger::getLogger()->warn("Cannot call method plugin_register_ingest "
					   "in loaded python module '%s'",
					   it->second->m_name.c_str());
		Py_CLEAR(pFunc);

		PyGILState_Release(state);
		return;
	}
	
	// Call Python method passing an object
	PyObject* ingest_fn = PyCapsule_New((void *)cb, NULL, NULL);
	PyObject* ingest_ref = PyCapsule_New((void *)data, NULL, NULL);
	PyObject* pReturn = PyObject_CallFunction(pFunc, "OOO", handle, ingest_fn, ingest_ref);

	Py_CLEAR(pFunc);
	Py_CLEAR(ingest_fn);

	// Handle returned data
	if (!pReturn)
	{
		Logger::getLogger()->error("Called python script method plugin_register_ingest "
					   ": error while getting result object, plugin '%s'",
					   it->second->m_name.c_str());
		logErrorMessage();
	}
	else
	{
		Logger::getLogger()->info("plugin_handle: plugin_register_ingest(): "
					  "got result object '%p', plugin '%s'",
					  pReturn,
					  it->second->m_name.c_str());
	}
	PyGILState_Release(state);
}

};

