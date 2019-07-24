/*
 * FogLAMP south plugin interface related
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Amandeep Singh Arora
 */

#include <logger.h>
#include <config_category.h>
#include <reading.h>
#include <mutex>
#include <south_plugin.h>
#include <Python.h>
#include <python_plugin_common_interface.h>

#define SHIM_SCRIPT_REL_PATH  "/python/foglamp/plugins/common/shim/shim.py"
#define SHIM_SCRIPT_NAME "shim"

using namespace std;

extern "C" {

extern PLUGIN_INFORMATION *plugin_info_fn();
extern PLUGIN_HANDLE plugin_init_fn(ConfigCategory *);
extern vector<Reading *> * plugin_poll_fn(PLUGIN_HANDLE);
extern void plugin_reconfigure_fn(PLUGIN_HANDLE*, const std::string&);
extern void plugin_shutdown_fn(PLUGIN_HANDLE);
extern void logErrorMessage();
extern PLUGIN_INFORMATION *Py2C_PluginInfo(PyObject *);

// South plugin entry points
void plugin_start_fn(PLUGIN_HANDLE handle);
void plugin_register_ingest_fn(PLUGIN_HANDLE handle,INGEST_CB2 cb,void * data);

Reading* Py2C_parseReadingObject(PyObject *);
vector<Reading *>* Py2C_getReadings(PyObject *);
DatapointValue* Py2C_createDictDPV(PyObject *data);
DatapointValue* Py2C_createListDPV(PyObject *data);
DatapointValue *Py2C_createBasicDPV(PyObject *dValue);

// Python object to instantiate
PyObject* pModule = NULL;

// PluginName
string sPluginName;

/**
 * Constructor for PythonPluginHandle
 *    - Load python 3.5 interpreter
 *    - Set sys.path and sys.argv
 *    - Import shim layer script and pass plugin name in argv[1]
 */
void *PluginInterfaceInit(const char *pluginName, const char * pluginPathName)
{
	// Set plugin name
	sPluginName = pluginName;
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
	Py_Initialize();
	PyEval_InitThreads();
	PyThreadState* save = PyEval_SaveThread(); // release Python GIT
	PyGILState_STATE state = PyGILState_Ensure();

	Logger::getLogger()->error("SouthPlugin PythonInterface %s:%d: "
				   "shimLayerPath=%s, foglampPythonDir=%s, plugin '%s'",
				   __FUNCTION__,
				   __LINE__,
				   shimLayerPath.c_str(),
				   foglampPythonDir.c_str(),
				   sPluginName.c_str());
	
	// Set Python path for embedded Python 3.5
	// Get current sys.path - borrowed reference
	PyObject* sysPath = PySys_GetObject((char *)"path");
	PyList_Append(sysPath, PyUnicode_FromString((char *) shimLayerPath.c_str()));
	PyList_Append(sysPath, PyUnicode_FromString((char *) foglampPythonDir.c_str()));

	// Set sys.argv for embedded Python 3.5
	int argc = 2;
	wchar_t* argv[2];
	argv[0] = Py_DecodeLocale("", NULL);
	argv[1] = Py_DecodeLocale(pluginName, NULL);
	PySys_SetArgv(argc, argv);

	// 2) Import Python script
	pModule = PyImport_ImportModule(name.c_str());

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
					   sPluginName.c_str());
	}
	else
	{
		Logger::getLogger()->debug("%s:%d: python module loaded successfully, pModule=%p, plugin '%s'",
					   __FUNCTION__,
					   __LINE__,
					   pModule,
					   sPluginName.c_str());
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
	else
	{
		Logger::getLogger()->fatal("PluginInterfaceResolveSymbol can not find symbol '%s' "
					   "in the South Python plugin interface library, loaded plugin '%s'",
					   _sym,
					   sPluginName.c_str());
		return NULL;
	}
}

/**
 * Function to invoke 'plugin_poll' function in python plugin
 *
 * @param    handle	Plugin handle from plugin_init_fn
 * @return		Vector of Reading data
 */
vector<Reading *> * plugin_poll_fn(PLUGIN_HANDLE handle)
{
	if (!pModule)
	{
		Logger::getLogger()->fatal("plugin_handle: plugin_poll(): "
					   "pModule is NULL for plugin '%s'",
					   sPluginName.c_str());
		return NULL;
	}
	if (!handle)
	{
		Logger::getLogger()->fatal("plugin_handle: plugin_poll(): "
					   "handle is NULL for plugin '%s'",
					   sPluginName.c_str());
		return NULL;
	}
	std::mutex mtx;
	PyObject* pFunc;
	lock_guard<mutex> guard(mtx);
	PyGILState_STATE state = PyGILState_Ensure();
	
	// Fetch required method in loaded object
	pFunc = PyObject_GetAttrString(pModule, "plugin_poll");
	if (!pFunc)
	{
		Logger::getLogger()->fatal("Cannot find 'plugin_poll' method "
					   "in loaded python module '%s'",
					   sPluginName.c_str());
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
					   sPluginName.c_str());
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
					   sPluginName.c_str());
		logErrorMessage();

		PyGILState_Release(state);
		return NULL;
	}
	else
	{
		// Get reading data
		vector<Reading *> *vec = Py2C_getReadings(pReturn);
		
		// Remove pReturn object
		Py_CLEAR(pReturn);

		PyGILState_Release(state);
		return vec;
	}
}
	
/**
 * Function to invoke 'plugin_start' function in python plugin
 *
 * @param    handle     Plugin handle from plugin_init_fn
 */
void plugin_start_fn(PLUGIN_HANDLE handle)
{
	if (!pModule)
	{
		Logger::getLogger()->fatal("plugin_handle: plugin_start(): "
					   "pModule is NULL for plugin '%s'",
					   sPluginName.c_str());
		return;
	}
	if (!handle)
	{
		Logger::getLogger()->fatal("plugin_handle: plugin_start(): "
					   "handle is NULL for plugin '%s'",
					   sPluginName.c_str());
		return;
	}
	PyObject* pFunc;
	PyGILState_STATE state = PyGILState_Ensure();
	
	// Fetch required method in loaded object
	pFunc = PyObject_GetAttrString(pModule, "plugin_start");
	if (!pFunc)
	{
		Logger::getLogger()->fatal("Cannot find 'plugin_start' method "
					   "in loaded python module '%s'",
					   sPluginName.c_str());
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
					   sPluginName.c_str());
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
					    sPluginName.c_str());
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
	if (!pModule)
	{
		Logger::getLogger()->fatal("plugin_handle: plugin_register_ingest(): "
					   "pModule is NULL for plugin '%s'",
					   sPluginName.c_str());
		return;
	}
	if (!handle)
	{
		Logger::getLogger()->fatal("plugin_handle: plugin_register_ingest(): "
					   "handle is NULL for plugin '%s'",
					   sPluginName.c_str());
		return;
	}
	PyObject* pFunc;
	PyGILState_STATE state = PyGILState_Ensure();
	
	// Fetch required method in loaded object
	pFunc = PyObject_GetAttrString(pModule, "plugin_register_ingest");
	if (!pFunc)
	{
		Logger::getLogger()->fatal("Cannot find 'plugin_register_ingest' "
					   "method in loaded python module '%s'",
					   sPluginName.c_str());
	}

	if (!pFunc || !PyCallable_Check(pFunc))
	{
		// Failure
		if (PyErr_Occurred())
		{
			logErrorMessage();
		}

		Logger::getLogger()->fatal("Cannot call method plugin_register_ingest "
					   "in loaded python module '%s'",
					   sPluginName.c_str());
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
					   sPluginName.c_str());
		logErrorMessage();
	}
	else
	{
		Logger::getLogger()->info("plugin_handle: plugin_register_ingest(): "
					  "got result object '%p', plugin '%s'",
					  pReturn,
					  sPluginName.c_str());
	}
	PyGILState_Release(state);
}

};

