/*
 * Fledge North plugin interface related
 *
 * Copyright (c) 2021 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Massimiliano Pinto
 */

#include <logger.h>
#include <config_category.h>
#include <reading.h>
#include <pythonreadingset.h>
#include <mutex>
#include <north_plugin.h>
#include <pyruntime.h>
#include <Python.h>
#include <python_plugin_common_interface.h>

#define SHIM_SCRIPT_NAME "north_shim"

using namespace std;

extern "C" {

extern PLUGIN_INFORMATION *plugin_info_fn();
extern PLUGIN_HANDLE plugin_init_fn(ConfigCategory *);
extern void plugin_reconfigure_fn(PLUGIN_HANDLE*, const std::string&);
extern void plugin_shutdown_fn(PLUGIN_HANDLE);
extern void logErrorMessage();
extern PLUGIN_INFORMATION *Py2C_PluginInfo(PyObject *);

// North plugin entry points
void plugin_start_fn(PLUGIN_HANDLE handle);
uint32_t plugin_send_fn(PLUGIN_HANDLE handle, const std::vector<Reading *>& readings);


/**
 * Function to invoke async 'plugin_send' function in python plugin
 *
 * @param   plugin_send_module_func Reference to plugin's plugin_send async method
 * @param   handle     Plugin handle from plugin_init_fn
 * @param   readingsList    Reading list to send
 */
unsigned int call_plugin_send_coroutine(PyObject *plugin_send_module_func, PLUGIN_HANDLE handle, PyObject *readingsList)
{
	unsigned int numSent=0;

	std::string fcn = "";
	fcn += "def plugin_send_wrapper(handle, readings, plugin_send_module_func):\n";
	fcn += "    import asyncio\n";
	fcn += "    loop = asyncio.new_event_loop()\n"; 
	fcn += "    asyncio.set_event_loop(loop)\n";
	fcn += "    coroObj = plugin_send_module_func(handle, readings, \"000001\")\n";
	fcn += "    futures = [coroObj]\n";
	fcn += "    done, result = loop.run_until_complete(asyncio.wait(futures))\n"; 
	fcn += "    numSent = 0\n";
	fcn += "    for t in done:\n";
	fcn += "        retCode, lastId, numSent = t.result()\n";
	fcn += "    return numSent\n";

	PyRun_SimpleString(fcn.c_str());
	PyObject* mod = PyImport_ImportModule("__main__");
	if (mod != NULL) 
	{
		PyObject* method = PyObject_GetAttrString(mod, "plugin_send_wrapper");
		if (method != NULL)
		{
			PyObject* arg = Py_BuildValue("OOO", handle, readingsList, plugin_send_module_func);
			PyObject* pReturn = PyObject_CallObject(method, arg);
			Logger::getLogger()->debug("%s:%d, pReturn=%p", __FUNCTION__, __LINE__, pReturn);
			Py_CLEAR(arg);
		    
			if (pReturn != NULL)
			{
				if(PyLong_Check(pReturn))
				{
					numSent = (long)PyLong_AsUnsignedLongMask(pReturn);
					Logger::getLogger()->debug("numSent=%d", numSent);
				}
				else
				{
					Logger::getLogger()->warn("plugin_send_wrapper() didn't return a number, returned value is of type %s", (Py_TYPE(pReturn))->tp_name);
				}	
				Py_CLEAR(pReturn);
			}
			else
			{
				Logger::getLogger()->debug("%s:%d: pReturn is NULL", __FUNCTION__, __LINE__);
				if (PyErr_Occurred())
				{
					logErrorMessage();
				}
			}
		}
		Py_CLEAR(method);
	}
        
	// Reset error
	PyErr_Clear();

	// Remove references
	Py_CLEAR(mod);

	return numSent;
}


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
    
	string northRootPath = fledgePythonDir + string(R"(/fledge/plugins/north/)") + string(pluginName);
	Logger::getLogger()->debug("%s:%d:, northRootPath=%s", __FUNCTION__, __LINE__, northRootPath.c_str());
    
	// Embedded Python 3.5 program name
	wchar_t *programName = Py_DecodeLocale(pluginName, NULL);
	Py_SetProgramName(programName);
	PyMem_RawFree(programName);

	PythonRuntime::getPythonRuntime();

	Logger::getLogger()->debug("%s:%d", __FUNCTION__, __LINE__);
    
	// Acquire GIL
	PyGILState_STATE state = PyGILState_Ensure();

	Logger::getLogger()->debug("NorthPlugin %s:%d: "
				   "northRootPath=%s, fledgePythonDir=%s, plugin '%s'",
				   __FUNCTION__,
				   __LINE__,
				   northRootPath.c_str(),
				   fledgePythonDir.c_str(),
				   pluginName);

	// Set Python path for embedded Python 3.x
	// Get current sys.path - borrowed reference
	PyObject* sysPath = PySys_GetObject((char *)"path");
	PyList_Append(sysPath, PyUnicode_FromString((char *) northRootPath.c_str()));
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
					   pluginName, northRootPath.c_str(),
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
								      PLUGIN_TYPE_NORTH,
								      // New Python interpteter not set
								      NULL)));
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
	else if (!sym.compare("plugin_shutdown"))
		return (void *) plugin_shutdown_fn;
	else if (!sym.compare("plugin_reconfigure"))
		return (void *) plugin_reconfigure_fn;
	else if (!sym.compare("plugin_start"))
		return (void *) plugin_start_fn;
	else if (!sym.compare("plugin_send"))
		return (void *) plugin_send_fn;
	else
	{
		Logger::getLogger()->fatal("PluginInterfaceResolveSymbol can not find symbol '%s' "
					   "in the North Python plugin interface library, loaded plugin '%s'",
					   _sym,
					   name.c_str());
		return NULL;
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

	// Take GIL
	PyGILState_STATE state = PyGILState_Ensure();
	
	// Fetch required method in loaded object
	pFunc = PyObject_GetAttrString(it->second->m_module, "plugin_start");
	if (!pFunc)
	{
		Logger::getLogger()->info("Cannot find 'plugin_start' method "
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

		Logger::getLogger()->info("Cannot call method 'plugin_start' "
					   "in loaded python module '%s'",
					   it->second->m_name.c_str());
		Py_CLEAR(pFunc);

		// Release GIL
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
		Logger::getLogger()->warn("Called python script method plugin_start : "
					   "error while getting result object, plugin '%s'",
					   it->second->m_name.c_str());
		logErrorMessage();
	}

	// Remore result object
	Py_CLEAR(pReturn);

	// Release GIL
	PyGILState_Release(state);
}

/**
 * Function to invoke 'plugin_send' function in python plugin
 *
 * @param    handle     Plugin handle from plugin_init_fn
 * @param    readings	Vector of readings data to send
 *
 * NOTE: currently doesn't work with async plugin_send
 */
uint32_t plugin_send_fn(PLUGIN_HANDLE handle, const std::vector<Reading *>& readings)
{

	uint32_t numReadingsSent = 0UL;
	if (!handle)
	{
		Logger::getLogger()->fatal("plugin_handle: plugin_send_fn: "
					   "handle is NULL");
		return numReadingsSent;
	}

	if (!pythonHandles)
	{
		// Plugin name can not be logged here
		Logger::getLogger()->error("pythonModules map is NULL "
					   "in plugin_send_fn, handle '%p'",
					   handle);
		 return numReadingsSent;
	}

	// Look for Python module for handle key
	auto it = pythonHandles->find(handle);
	if (it == pythonHandles->end() ||
	    !it->second ||
	    !it->second->m_module)
	{
		Logger::getLogger()->fatal("plugin_handle: plugin_send(): "
					   "pModule is NULL, plugin handle '%p'",
					   handle);
		return numReadingsSent;
	}

	// We have plugin name
	string pName = it->second->m_name;

	PyObject* pFunc;

	// Take GIL
	PyGILState_STATE state = PyGILState_Ensure();

	// Fetch required method in loaded object
	pFunc = PyObject_GetAttrString(it->second->m_module, "plugin_send");
	if (!pFunc)
	{
		Logger::getLogger()->fatal("Cannot find 'plugin_send' "
					   "method in loaded python module '%s'",
					   pName.c_str());
		PyGILState_Release(state);
		return numReadingsSent;
	}

	if (!pFunc || !PyCallable_Check(pFunc))
	{
	        // Failure
		if (PyErr_Occurred())
		{
			logErrorMessage();
		}

		Logger::getLogger()->fatal("Cannot call method plugin_send"
					   "in loaded python module '%s'",
					   pName.c_str());
		Py_CLEAR(pFunc);

		// Release GIL
		PyGILState_Release(state);
		return numReadingsSent;
	}

	// 1. create a ReadingSet
	ReadingSet set(&readings);

	// 2. create a PythonReadingSet object
	PythonReadingSet *pyReadingSet = (PythonReadingSet *) &set;

	// 3. create PyObject
	PyObject* readingsList = pyReadingSet->toPython(true);
	    
	numReadingsSent = call_plugin_send_coroutine(pFunc, handle, readingsList);
	Logger::getLogger()->debug("C2Py: plugin_send_fn():L%d: filtered readings sent %d",
				__LINE__,
				numReadingsSent);

	set.clear(); // to avoid deletion of contained Reading objects; they are subsequently accessed in calling function DataSender::send()

	// Remove python object
	Py_CLEAR(readingsList);
	Py_CLEAR(pFunc);

	// Release GIL
	PyGILState_Release(state);

	// Return the number of readings sent
	return numReadingsSent;
}

};

