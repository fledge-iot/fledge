/*
 * FogLAMP south plugin interface related
 *
 * Copyright (c) 2018 OSisoft, LLC
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

#define SHIM_SCRIPT_REL_PATH  "/python/foglamp/plugins/common/shim/shim.py"
#define SHIM_SCRIPT_NAME "shim"

#define PRINT_FUNC	Logger::getLogger()->info("%s:%d", __FUNCTION__, __LINE__);

using namespace std;

extern "C" {

PLUGIN_INFORMATION *plugin_info_fn();
PLUGIN_HANDLE plugin_init_fn(ConfigCategory *);
vector<Reading *> * plugin_poll_fn(PLUGIN_HANDLE);
void plugin_reconfigure_fn(PLUGIN_HANDLE*, const std::string&);
void plugin_shutdown_fn(PLUGIN_HANDLE);

PLUGIN_INFORMATION *Py2C_PluginInfo(PyObject *);
Reading* Py2C_parseReadingObject(PyObject *);
vector<Reading *>* Py2C_getReadings(PyObject *);


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
		Logger::getLogger()->fatal("PythonPluginHandle c'tor: cannot import Python 3.5 script "
					   "'%s' from '%s' : pythonScript=%s, shimLayerPath=%s",
					   name.c_str(), path.c_str(),
					   pythonScript.c_str(),
					   shimLayerPath.c_str());
	}
	else
		Logger::getLogger()->info("%s:%d: python module loaded successfully, pModule=%p", __FUNCTION__, __LINE__, pModule);

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
	return info;
}

/**
 * Function to invoke 'plugin_init' function in python plugin
 */
PLUGIN_HANDLE plugin_init_fn(ConfigCategory *config)
{
	PyObject* pFunc;
	
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

		return NULL;
	}
	else
	{
		Logger::getLogger()->info("plugin_handle: plugin_init(): got handle from python plugin='%p'", pReturn);
		
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

		return NULL;
	}
	else
	{
		// Get reading data
		vector<Reading *> *vec = Py2C_getReadings(pReturn);
		//Logger::getLogger()->info("plugin_poll_fn: reading='%s'", rdng->toJSON().c_str());
		
		// Remove pReturn object
		Py_CLEAR(pReturn);

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
		
		return;
	}
}


/**
 * Function to invoke 'plugin_shutdown' function in python plugin
 */
void plugin_shutdown_fn(PLUGIN_HANDLE handle)
{
	PyObject* pFunc;
	
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
		 /*if (!PyBytes_Check(dKey) || !PyBytes_Check(dValue))
		  {
			Logger::getLogger()->info("3. PyDict: dKey & dValue are not of required type");
			continue;
		  }*/
		char* ckey = PyUnicode_AsUTF8(dKey);
		char* cval = PyUnicode_AsUTF8(dValue);
		//char *emptyStr = new char[1];
		//emptyStr[0] = '\0';
		//cval = PyUnicode_AsUTF8(dValue);
		//Logger::getLogger()->info("4. PyDict: ckey=%s, cval=%s", ckey, cval);

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
 * Creating Reading object from Python object
 *
 * @param element	Python 3.5 Object (dict)
 * @return		Pointer to a new Reading object
 *				or NULL in case of errors
 */
Reading* Py2C_parseReadingObject(PyObject *element)
{
	// Get list item: borrowed reference.
	if (!element)
	{
		// Failure
		if (PyErr_Occurred())
		{
			logErrorMessage();
		}
		return NULL;
	}
	if (!PyDict_Check(element))
	{
		// Failure
		if (PyErr_Occurred())
		{
			logErrorMessage();
		}
		return NULL;
	}

	// Get 'asset_code' value: borrowed reference.
	PyObject* assetCode = PyDict_GetItemString(element,
						   "asset");
	// Get 'reading' value: borrowed reference.
	PyObject* reading = PyDict_GetItemString(element,
						 "readings");
	// Keys not found or reading is not a dict
	if (!assetCode ||
		!reading ||
		!PyDict_Check(reading))
	{
		// Failure
		if (PyErr_Occurred())
		{
			logErrorMessage();
		}
		return NULL;
	}

	//Logger::getLogger()->info("Py2C_parseReadingObject: asset_code=%s, reading is a python dict", PyUnicode_AsUTF8(assetCode));

	// Fetch all Datapoins in 'reading' dict			
	PyObject *dKey, *dValue;  // borrowed references set by PyDict_Next()
	Py_ssize_t dPos = 0;
	Reading* newReading = NULL;

	// Fetch all Datapoints in 'reading' dict
	// dKey and dValue are borrowed references
	while (PyDict_Next(reading, &dPos, &dKey, &dValue))
	{
		DatapointValue* dataPoint;
		if (PyLong_Check(dValue) || PyLong_Check(dValue))
		{
			dataPoint = new DatapointValue((long)PyLong_AsUnsignedLongMask(dValue));
		}
		else if (PyFloat_Check(dValue))
		{
			dataPoint = new DatapointValue(PyFloat_AS_DOUBLE(dValue));
		}
		else if (PyBytes_Check(dValue))
		{
			dataPoint = new DatapointValue(string(PyUnicode_AsUTF8(dValue)));
		}
		else if (PyUnicode_Check(dValue))
		{
			dataPoint = new DatapointValue(string(PyUnicode_AsUTF8(dValue)));
		}
		else
		{
			Logger::getLogger()->info("Unable to parse dValue in readings dict: dKey=%s, Py_TYPE(dValue)=%s", string(PyUnicode_AsUTF8(dKey)).c_str(), (Py_TYPE(dValue))->tp_name);
			//delete dataPoint;
			return NULL;
		}

		// Add / Update the new Reading data			
		if (newReading == NULL)
		{
			newReading = new Reading(string(PyUnicode_AsUTF8(assetCode)),
						 new Datapoint(string(PyUnicode_AsUTF8(dKey)),
								   *dataPoint));
		}
		else
		{
			newReading->addDatapoint(new Datapoint(string(PyUnicode_AsUTF8(dKey)),
								   *dataPoint));
		}

		/**
		 * Set id, uuid, ts and user_ts of the original data
		 */

		// Get 'id' value: borrowed reference.
		PyObject* id = PyDict_GetItemString(element, "id");
		if (id && PyLong_Check(id))
		{
			// Set id
			newReading->setId(PyLong_AsUnsignedLong(id));
		}

		// Get 'ts' value: borrowed reference.
		PyObject* ts = PyDict_GetItemString(element, "ts");
		if (ts)
		{
			// Convert a timestamp of the from 2019-01-07 19:06:35.366100+01:00
			char *ts_str = PyUnicode_AsUTF8(ts);
			newReading->setTimestamp(ts_str);
		}

		// Get 'user_ts' value: borrowed reference.
		PyObject* uts = PyDict_GetItemString(element, "timestamp");
		if (uts)
		{
			// Convert a timestamp of the from 2019-01-07 19:06:35.366100+01:00
			char *ts_str = PyUnicode_AsUTF8(uts);
			newReading->setUserTimestamp(ts_str);
		}




		// Get 'uuid' value: borrowed reference.
		PyObject* uuid = PyDict_GetItemString(element, "key");
		if (uuid && PyUnicode_Check(uuid))
		{
			// Set uuid
			newReading->setUuid(string(PyUnicode_AsUTF8(uuid)));
		}

		// Remove temp objects
		delete dataPoint;
	}
	return newReading;
}

/**
 * Creating Reading object from Python object
 *
 * @param element	Python 3.5 Object (dict)
 * @return		Pointer to a new Reading object
 *				or NULL in case of errors
 */
vector<Reading *>* Py2C_getReadings(PyObject *polledData)
{
	vector<Reading *>* newReadings = new vector<Reading *>();

	if(PyList_Check(polledData)) // got a list of readings
	{
		// Iterate reading objects in the list
		for (int i = 0; i < PyList_Size(polledData); i++)
		{
			// Get list item: borrowed reference.
			PyObject* element = PyList_GetItem(polledData, i);
			if (!element)
			{
				// Failure
				if (PyErr_Occurred())
				{
					logErrorMessage();
				}
				delete newReadings;

				return NULL;
			}
			Reading* newReading = Py2C_parseReadingObject(element);
			if (newReading)
			{
				// Add the new reading to result vector
				newReadings->push_back(newReading);
			}
			else
				Logger::getLogger()->info("Py2C_getReadings: Reading[%d] is NULL", i);
		}
	}
	else // just a single reading, no list
	{
		Reading* newReading = Py2C_parseReadingObject(polledData);
		if (newReading)
			newReadings->push_back(newReading);
	}
	
	return newReadings;
	
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

	// NOTE from :
	// https://docs.python.org/2/c-api/exceptions.html
	//
	// The value and traceback object may be NULL
	// even when the type object is not.	
	const char* pErrorMessage = pValue ?
				    PyBytes_AsString(pValue) :
				    "no error description.";

	Logger::getLogger()->fatal("logErrorMessage: Error '%s' ",
				   pErrorMessage ?
				   pErrorMessage :
				   "no description");

	// Reset error
	PyErr_Clear();

	// Remove references
	Py_CLEAR(pType);
	Py_CLEAR(pValue);
	Py_CLEAR(pTraceback);
}
};

