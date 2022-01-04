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

// Reading* Py2C_parseReadingObject(PyObject *);
//vector<Reading *>* Py2C_getReadings(PyObject *);
// DatapointValue* Py2C_createDictDPV(PyObject *data);
// DatapointValue* Py2C_createListDPV(PyObject *data);
// DatapointValue *Py2C_createBasicDPV(PyObject *dValue);

/**
 * Constructor for PythonPluginHandle
 *    - Load python 3.5 interpreter
 *    - Set sys.path and sys.argv
 *    - Import shim layer script and pass plugin name in argv[1]
 */
void *PluginInterfaceInit(const char *pluginName, const char * pluginPathName)
{
	bool initialisePython = false;

	// Set plugin name, also for methods in common-plugin-interfaces/python
	gPluginName = pluginName;
	// Get FLEDGE_ROOT dir
	string fledgeRootDir(getenv("FLEDGE_ROOT"));

	string path = fledgeRootDir + SHIM_SCRIPT_REL_PATH;
	string name(string(PLUGIN_TYPE_NORTH) + string(SHIM_SCRIPT_POSTFIX));
	
	// Python 3.5  script name
	std::size_t found = path.find_last_of("/");
	string pythonScript = path.substr(found + 1);
	string shimLayerPath = path.substr(0, found);
	
	// Embedded Python 3.5 program name
	wchar_t *programName = Py_DecodeLocale(name.c_str(), NULL);
	Py_SetProgramName(programName);
	PyMem_RawFree(programName);

	string fledgePythonDir = fledgeRootDir + "/python";
	
	PythonRuntime::getPythonRuntime();


	// Note: for North service plugin we don't set a new Python interpreter

	Logger::getLogger()->debug("NorthPlugin PythonInterface %s:%d: "
				   "shimLayerPath=%s, fledgePythonDir=%s, plugin '%s'",
				   __FUNCTION__,
				   __LINE__,
				   shimLayerPath.c_str(),
				   fledgePythonDir.c_str(),
				   pluginName);
	
	// Take GIL
	PyGILState_STATE state = PyGILState_Ensure();

	// Set Python path for embedded Python 3.5
	// Get current sys.path - borrowed reference
	PyObject* sysPath = PySys_GetObject((char *)"path");
	PyList_Append(sysPath, PyUnicode_FromString((char *) shimLayerPath.c_str()));
	PyList_Append(sysPath, PyUnicode_FromString((char *) fledgePythonDir.c_str()));

	// Set sys.argv for embedded Python 3.5
	int argc = 2;
	wchar_t* argv[2];
	argv[0] = Py_DecodeLocale("", NULL);
	argv[1] = Py_DecodeLocale(pluginName, NULL);
	PySys_SetArgv(argc, argv);

	// 2) Import Python script
	PyObject *pModule = PyImport_ImportModule(name.c_str());

	// Check whether the Python module has been imported
	if (!pModule)
	{
		// Failure
		if (PyErr_Occurred())
		{
			logErrorMessage();
		}
		Logger::getLogger()->fatal("PluginInterfaceInit: cannot import Python 3.5 script "
					   "'%s' from '%s' : pythonScript=%s, shimLayerPath=%s, plugin '%s'",
					   name.c_str(), path.c_str(),
					   pythonScript.c_str(),
					   shimLayerPath.c_str(),
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
		Logger::getLogger()->fatal("Cannot find 'plugin_start' method "
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

		Logger::getLogger()->fatal("Cannot call method 'plugin_start' "
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
		Logger::getLogger()->error("Called python script method plugin_start : "
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

	uint32_t data = 0UL;
	if (!handle)
	{
		Logger::getLogger()->fatal("plugin_handle: plugin_send_fn: "
					   "handle is NULL");
		return data;
	}

	if (!pythonHandles)
	{
		// Plugin name can not be logged here
		Logger::getLogger()->error("pythonModules map is NULL "
					   "in plugin_send_fn, handle '%p'",
					   handle);
		 return data;
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
		return data;
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
	}

	if (!pFunc || !PyCallable_Check(pFunc))
	{
	        // Failure
		if (PyErr_Occurred())
		{
			logErrorMessage();
		}

		Logger::getLogger()->fatal("Cannot call method plugin_ingest"
					   "in loaded python module '%s'",
					   pName.c_str());
		Py_CLEAR(pFunc);

		// Release GIL
		PyGILState_Release(state);
		return data;
	}

    // Create a dict of readings
	// - 1 - Create Python list of dicts as input to the filter
	ReadingSet *set = new ReadingSet(&readings);
	PythonReadingSet *pyReadingSet = (PythonReadingSet *) set;
    Logger::getLogger()->info("%s:%d", __FUNCTION__, __LINE__);
    PyObject* readingsList = pyReadingSet->toPython();
    Logger::getLogger()->info("%s:%d", __FUNCTION__, __LINE__);
    PyObject* objectsRepresentation = PyObject_Repr(readingsList);
    const char* s = PyUnicode_AsUTF8(objectsRepresentation);
    Logger::getLogger()->info("C2Py: plugin_send_fn():L%d: readingsList=%s", __LINE__, s);
    Py_CLEAR(objectsRepresentation);
    
	// Create the object with readings content (with "asset_code" and "reading" keys)
	// PyObject *readingsList = createReadingsList(readings, true);
    
	// Fetch result
	PyObject* pReturn = PyObject_CallFunction(pFunc,
						  "OO",
						  handle,
						  readingsList);
	Py_CLEAR(pFunc);

	// Handle returned data
	if (!pReturn)
	{
		Logger::getLogger()->error("Called python script method plugin_send "
					   ": error while getting result object, plugin '%s'",
					   pName.c_str());
		logErrorMessage();

		// Remove readings to dict
		Py_CLEAR(readingsList);

		// Release GIL
		PyGILState_Release(state);

		return data;
	}

	// Check return type
	if(PyLong_Check(pReturn))
	{
		data = (long)PyLong_AsUnsignedLongMask(pReturn);	
	}

	// Remove readings to dict
	Py_CLEAR(readingsList);

	// Remnove result object
	Py_CLEAR(pReturn);

	// Release GIL
	PyGILState_Release(state);

	// Return the number of readings sent
	return data;
}

};

