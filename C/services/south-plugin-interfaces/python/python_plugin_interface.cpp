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
#include <python_plugin_handle.h>
#include <south_plugin.h>

#define SHIM_SCRIPT_REL_PATH  "/python/foglamp/plugins/common/shim/shim.py"
#define SHIM_SCRIPT_NAME "shim"

using namespace std;

extern "C" {

PLUGIN_INFORMATION *plugin_info_fn();
PLUGIN_HANDLE plugin_init_fn(ConfigCategory *);
vector<Reading *> * plugin_poll_fn(PLUGIN_HANDLE);
void plugin_reconfigure_fn(PLUGIN_HANDLE*, const std::string&);
void plugin_shutdown_fn(PLUGIN_HANDLE);
void plugin_start_fn(PLUGIN_HANDLE handle);
void plugin_register_ingest_fn(PLUGIN_HANDLE handle,INGEST_CB2 cb,void * data);

PLUGIN_INFORMATION *Py2C_PluginInfo(PyObject *);
Reading* Py2C_parseReadingObject(PyObject *);
vector<Reading *>* Py2C_getReadings(PyObject *);
DatapointValue* Py2C_createDictDPV(PyObject *data);
DatapointValue* Py2C_createListDPV(PyObject *data);
DatapointValue *Py2C_createBasicDPV(PyObject *dValue);



static void logErrorMessage();

PyObject* pModule;

// mutex between reconfigure and poll, since reconfigure changes the handle 
// object itself and marks previous handle as garbage collectible by Python runtime
std::mutex mtx;

/**
 * Constructor for PythonPluginHandle
 *    - Load python 3.5 interpreter
 *    - Set sys.path and sys.argv
 *    - Import shim layer script and pass plugin name in argv[1]
 */
void *PluginInterfaceInit(const char *pluginName, const char * /*_path*/)
{
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

	Logger::getLogger()->info("%s:%d: shimLayerPath=%s, foglampPythonDir=%s", __FUNCTION__, __LINE__, shimLayerPath.c_str(), foglampPythonDir.c_str());
	
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
					   "'%s' from '%s' : pythonScript=%s, shimLayerPath=%s",
					   name.c_str(), path.c_str(),
					   pythonScript.c_str(),
					   shimLayerPath.c_str());
	}
	else
		Logger::getLogger()->info("%s:%d: python module loaded successfully, pModule=%p", __FUNCTION__, __LINE__, pModule);

	PyGILState_Release(state);
	return pModule;
}

/**
 * Destructor for PythonPluginHandle
 *    - Free up owned references
 *    - Unload python 3.5 interpreter
 */
void PluginInterfaceCleanup()
{
	// Decrement pModule reference count
	Py_CLEAR(pModule);

	// Cleanup Python 3.5
	Py_Finalize();
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
		Logger::getLogger()->info("PluginInterfaceResolveSymbol returning NULL for sym=%s", _sym);
		return NULL;
	}
}

/**
 * Returns function pointer that can be invoked to call 'plugin_info'
 * function in python plugin
 */
void* PluginInterfaceGetInfo()
{
	return (void *) plugin_info_fn;
}

/**
 * Function to invoke 'plugin_info' function in python plugin
 */
PLUGIN_INFORMATION *plugin_info_fn()
{
	PyObject* pFunc;
	PyGILState_STATE state = PyGILState_Ensure();
	
	// Fetch required method in loaded object
	pFunc = PyObject_GetAttrString(pModule, "plugin_info");
	if (!pModule || !pFunc)
		Logger::getLogger()->info("plugin_handle: plugin_info(): pModule=%p, pFunc=%p", pModule, pFunc);

	if (!pFunc || !PyCallable_Check(pFunc))
	{
		// Failure
		if (PyErr_Occurred())
		{
			logErrorMessage();
		}

		Logger::getLogger()->fatal("Cannot find method plugin_info in loaded python module");
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
		Logger::getLogger()->error("Called python script method plugin_info : error while getting result object");
		logErrorMessage();
		info = NULL;
	}
	else
	{	
		// Parse plugin information
		info = Py2C_PluginInfo(pReturn);
		
		// bump interface version to atleast 2.x so that we are able to handle list of readings from python plugins in plugin_poll
		if (info->interface[0]=='1' && info->interface[1]=='.')
		{
			Logger::getLogger()->info("plugin_handle: plugin_info(): Updating interface version from '%s' to '2.0.0' ", info->interface);
			delete info->interface;
			char *valStr = new char[6];
			std::strcpy(valStr, "2.0.0");
			info->interface = valStr;
		}
		
		// Remove pReturn object
		Py_CLEAR(pReturn);
	}
	if(info)
		Logger::getLogger()->info("plugin_handle: plugin_info(): info={name=%s, version=%s, options=%d, type=%s, interface=%s, config=%s}", 
					info->name, info->version, info->options, info->type, info->interface, info->config);
	PyGILState_Release(state);
	return info;
}

/**
 * Function to invoke 'plugin_init' function in python plugin
 */
PLUGIN_HANDLE plugin_init_fn(ConfigCategory *config)
{
	PyObject* pFunc;
	PyGILState_STATE state = PyGILState_Ensure();
	
	// Fetch required method in loaded object
	pFunc = PyObject_GetAttrString(pModule, "plugin_init");
	if (!pModule || !pFunc)
		Logger::getLogger()->info("plugin_handle: plugin_init(): pModule=%p, pFunc=%p", pModule, pFunc);

	if (!pFunc || !PyCallable_Check(pFunc))
	{
		// Failure
		if (PyErr_Occurred())
		{
			logErrorMessage();
		}

		Logger::getLogger()->fatal("Cannot find method plugin_init in loaded python module");
		Py_CLEAR(pFunc);

		PyGILState_Release(state);
		return NULL;
	}

	Logger::getLogger()->info("plugin_handle: plugin_init(): config->itemsToJSON()='%s'", config->itemsToJSON().c_str());
	
	// Call Python method passing an object
	PyObject* pReturn = PyObject_CallFunction(pFunc, "s", config->itemsToJSON().c_str());

	Py_CLEAR(pFunc);

	// Handle returned data
	if (!pReturn)
	{
		Logger::getLogger()->error("Called python script method plugin_init : error while getting result object");
		logErrorMessage();

		PyGILState_Release(state);
		return NULL;
	}
	else
	{
		Logger::getLogger()->info("plugin_handle: plugin_init(): got handle from python plugin='%p'", pReturn);
		
		PyGILState_Release(state);
		return (PLUGIN_HANDLE) pReturn;
	}
}

/**
 * Function to invoke 'plugin_poll' function in python plugin
 */
vector<Reading *> * plugin_poll_fn(PLUGIN_HANDLE handle)
{
	PyObject* pFunc;
	lock_guard<mutex> guard(mtx);
	PyGILState_STATE state = PyGILState_Ensure();
	
	// Fetch required method in loaded object
	pFunc = PyObject_GetAttrString(pModule, "plugin_poll");
	if (!pModule || !pFunc || !handle)
	{
		if (handle)
			Logger::getLogger()->info("plugin_handle: plugin_poll(): pModule=%p, pFunc=%p", pModule, pFunc);
		return NULL;
	}

	if (!pFunc || !PyCallable_Check(pFunc))
	{
		// Failure
		if (PyErr_Occurred())
		{
			logErrorMessage();
		}

		Logger::getLogger()->fatal("Cannot find method plugin_poll in loaded python module");
		Py_CLEAR(pFunc);

		PyGILState_Release(state);
		return NULL;
	}

	// Call Python method passing an object
	PyObject* pReturn = PyObject_CallFunction(pFunc, "O", handle);

	Py_CLEAR(pFunc);

	// Handle returned data
	if (!pReturn)
	{
		// Errors while getting result object
		Logger::getLogger()->error("Called python script method plugin_poll : error while getting result object");
		logErrorMessage();

		PyGILState_Release(state);
		return NULL;
	}
	else
	{
		// Get reading data
		vector<Reading *> *vec = Py2C_getReadings(pReturn);
		//Logger::getLogger()->info("plugin_poll_fn: reading='%s'", rdng->toJSON().c_str());
		
		// Remove pReturn object
		Py_CLEAR(pReturn);

		PyGILState_Release(state);
		return vec;
	}
}
	

/**
 * Function to invoke 'plugin_reconfigure' function in python plugin
 */
void plugin_reconfigure_fn(PLUGIN_HANDLE* handle, const std::string& config)
{
	PyObject* pFunc;
	lock_guard<mutex> guard(mtx);
	PyGILState_STATE state = PyGILState_Ensure();

	//Logger::getLogger()->info("plugin_handle: plugin_reconfigure(): pModule=%p, *handle=%p", pModule, *handle);
	
	// Fetch required method in loaded object
	pFunc = PyObject_GetAttrString(pModule, "plugin_reconfigure");
	if (!pModule || !pFunc)
		Logger::getLogger()->info("plugin_handle: plugin_reconfigure(): pModule=%p, pFunc=%p", pModule, pFunc);

	if (!pFunc || !PyCallable_Check(pFunc))
	{
		// Failure
		if (PyErr_Occurred())
		{
			logErrorMessage();
		}

		Logger::getLogger()->fatal("Cannot find method plugin_reconfigure in loaded python module");
		Py_CLEAR(pFunc);

		PyGILState_Release(state);
		return;
	}

	// Call Python method passing an object
	PyObject* pReturn = PyObject_CallFunction(pFunc, "Os", *handle, config.c_str());

	Py_CLEAR(pFunc);

	// Handle returned data
	if (!pReturn)
	{
		Logger::getLogger()->error("Called python script method plugin_reconfigure : error while getting result object");
		logErrorMessage();
		*handle = NULL; // not sure if this should be treated as unrecoverable failure on python plugin side
		return;
	}
	else
	{
		Py_CLEAR(*handle);
		*handle = pReturn;
		Logger::getLogger()->info("plugin_handle: plugin_reconfigure(): got updated handle from python plugin=%p", *handle);
	}
	PyGILState_Release(state);
	return;
}


/**
 * Function to invoke 'plugin_shutdown' function in python plugin
 */
void plugin_shutdown_fn(PLUGIN_HANDLE handle)
{
	PyObject* pFunc;
	PyGILState_STATE state = PyGILState_Ensure();
	
	// Fetch required method in loaded object
	pFunc = PyObject_GetAttrString(pModule, "plugin_shutdown");
	if (!pModule || !pFunc || !handle)
	{
		if (handle)
			Logger::getLogger()->info("plugin_handle: plugin_shutdown(): pModule=%p, pFunc=%p", pModule, pFunc);
		return;
	}

	if (!pFunc || !PyCallable_Check(pFunc))
	{
		// Failure
		if (PyErr_Occurred())
		{
			logErrorMessage();
		}

		Logger::getLogger()->fatal("Cannot find method plugin_shutdown in loaded python module");
		Py_CLEAR(pFunc);
	
		PyGILState_Release(state);
		return;
	}

	// Call Python method passing an object
	PyObject* pReturn = PyObject_CallFunction(pFunc, "O", handle);

	Py_CLEAR(pFunc);

	// Handle return
	if (!pReturn)
	{
		Logger::getLogger()->error("Called python script method plugin_shutdown : error while getting result object");
		logErrorMessage();
	}
	PyGILState_Release(state);
}


/**
 * Function to invoke 'plugin_start' function in python plugin
 */
void plugin_start_fn(PLUGIN_HANDLE handle)
{
	PyObject* pFunc;
	PyGILState_STATE state = PyGILState_Ensure();
	
	// Fetch required method in loaded object
	pFunc = PyObject_GetAttrString(pModule, "plugin_start");
	if (!pModule || !pFunc)
		Logger::getLogger()->info("plugin_handle: plugin_start(): pModule=%p, pFunc=%p", pModule, pFunc);

	if (!pFunc || !PyCallable_Check(pFunc))
	{
		// Failure
		if (PyErr_Occurred())
		{
			logErrorMessage();
		}

		Logger::getLogger()->fatal("Cannot find method plugin_start in loaded python module");
		Py_CLEAR(pFunc);

		PyGILState_Release(state);
		return;
	}

	// Call Python method passing an object
	PyObject* pReturn = PyObject_CallFunction(pFunc, "O", handle);

	Py_CLEAR(pFunc);

	// Handle return
	if (!pReturn)
	{
		Logger::getLogger()->error("Called python script method plugin_start : error while getting result object");
		logErrorMessage();
	}
	PyGILState_Release(state);
}


/**
 * Function to invoke 'plugin_register_ingest' function in python plugin
 */
void plugin_register_ingest_fn(PLUGIN_HANDLE handle, INGEST_CB2 cb, void *data)
{
	PyObject* pFunc;
	PyGILState_STATE state = PyGILState_Ensure();
	
	// Fetch required method in loaded object
	pFunc = PyObject_GetAttrString(pModule, "plugin_register_ingest");
	if (!pModule || !pFunc)
		Logger::getLogger()->info("plugin_handle: plugin_register_ingest(): pModule=%p, pFunc=%p", pModule, pFunc);

	if (!pFunc || !PyCallable_Check(pFunc))
	{
		// Failure
		if (PyErr_Occurred())
		{
			logErrorMessage();
		}

		Logger::getLogger()->fatal("Cannot find method plugin_register_ingest in loaded python module");
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
		Logger::getLogger()->error("Called python script method plugin_register_ingest : error while getting result object");
		logErrorMessage();
	}
	else
	{
		Logger::getLogger()->info("plugin_handle: plugin_register_ingest(): got result object '%p' ", pReturn);
	}
	PyGILState_Release(state);
}

/**
 * Fill PLUGIN_INFORMATION structure from Python object
 *
 * @param pyRetVal	Python 3.5 Object (dict)
 * @return		Pointer to a new PLUGIN_INFORMATION structure
 *				or NULL in case of errors
 */
PLUGIN_INFORMATION *Py2C_PluginInfo(PyObject* pyRetVal)
{
	// Create returnable PLUGIN_INFORMATION structure
	PLUGIN_INFORMATION *info = new PLUGIN_INFORMATION;

	PyObject *dKey, *dValue; // these are borrowed references returned by PyDict_Next
	Py_ssize_t dPos = 0;
	
	// dKey and dValue are borrowed references
	while (PyDict_Next(pyRetVal, &dPos, &dKey, &dValue))
	{
		char* ckey = PyUnicode_AsUTF8(dKey);
		char* cval = PyUnicode_AsUTF8(dValue);
		//Logger::getLogger()->info("Py2C_PluginInfo: ckey=%s, cval=%s", ckey, cval);

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
			info->options |= SP_ASYNC;
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
 * Function to log error message encountered while interfacing with
 * Python runtime
 */
static void logErrorMessage()
{
	//Get error message
	PyObject *pType, *pValue, *pTraceback;
	PyErr_Fetch(&pType, &pValue, &pTraceback);
	PyErr_NormalizeException(&pType, &pValue, &pTraceback);

	PyObject* str_exc_value = PyObject_Repr(pValue);
	PyObject* pyExcValueStr = PyUnicode_AsEncodedString(str_exc_value, "utf-8", "Error ~");
	const char* pErrorMessage = pValue ?
				    PyBytes_AsString(pyExcValueStr) :
				    "no error description.";
	Logger::getLogger()->fatal("logErrorMessage: Error '%s' ", pErrorMessage);

	// Reset error
	PyErr_Clear();

	// Remove references
	Py_CLEAR(pType);
	Py_CLEAR(pValue);
	Py_CLEAR(pTraceback);
	Py_CLEAR(str_exc_value);
	Py_CLEAR(pyExcValueStr);
}
};

