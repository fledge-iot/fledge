/*
 * FogLAMP plugin handle related
 *
 * Copyright (c) 2018 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Amandeep Singh Arora
 */

#include <iostream>
#include <unordered_map>
#include <logger.h>
#include <config_category.h>
#include <reading.h>
#include <logger.h>
#include <utils.h>
#include <plugin_handle.h>

//#include <Python.h>

#define PRINT_FUNC	Logger::getLogger()->info("%s:%d", __FUNCTION__, __LINE__);

PLUGIN_INFORMATION *Py2C_PluginInfo(PyObject* pyRetVal);
static void logErrorMessage();
PLUGIN_INFORMATION *plugin_info_fn();
PLUGIN_HANDLE plugin_init_fn(ConfigCategory *config);
void plugin_shutdown_fn(PLUGIN_HANDLE);
Reading plugin_poll_fn(PLUGIN_HANDLE);

using namespace std;

#if 0
	// Setup the function pointers to the plugin
  	pluginStartPtr = (void (*)(PLUGIN_HANDLE))
				manager->resolveSymbol(handle, "plugin_start");
  	pluginPollPtr = (Reading (*)(PLUGIN_HANDLE))
				manager->resolveSymbol(handle, "plugin_poll");
  	pluginReconfigurePtr = (void (*)(PLUGIN_HANDLE, const std::string&))
				manager->resolveSymbol(handle, "plugin_reconfigure");
  	pluginShutdownPtr = (void (*)(PLUGIN_HANDLE))
				manager->resolveSymbol(handle, "plugin_shutdown");
	if (isAsync())
	{
  		pluginRegisterPtr = (void (*)(PLUGIN_HANDLE, INGEST_CB cb, void *data))
				manager->resolveSymbol(handle, "plugin_register_ingest");
	}

	pluginShutdownDataPtr = (string (*)(const PLUGIN_HANDLE))
				 manager->resolveSymbol(handle, "plugin_shutdown");
	pluginStartDataPtr = (void (*)(const PLUGIN_HANDLE, const string& storedData))
			      manager->resolveSymbol(handle, "plugin_start");
#endif


typedef enum {
	PLUGIN_INIT,
	PLUGIN_START,
	PLUGIN_POLL,
	PLUGIN_RECONF,
	PLUGIN_SHUTDOWN,
	PLUGIN_REGISTER
} PluginFuncType;

std::unordered_map<std::string, PluginFuncType> pluginFuncTypeMap = {
															{"plugin_init", PLUGIN_INIT}, 
															{"plugin_start", PLUGIN_START}, 
															{"plugin_poll", PLUGIN_POLL}, 
															{"plugin_reconfigure", PLUGIN_RECONF}, 
															{"plugin_shutdown", PLUGIN_SHUTDOWN}, 
															{"plugin_register_ingest", PLUGIN_REGISTER}
														  };

#if 0
	void		(*pluginStartPtr)(PLUGIN_HANDLE);
	Reading		(*pluginPollPtr)(PLUGIN_HANDLE);
	void		(*pluginReconfigurePtr)(PLUGIN_HANDLE,
					        const std::string& newConfig);
	void		(*pluginShutdownPtr)(PLUGIN_HANDLE);
	void		(*pluginRegisterPtr)(PLUGIN_HANDLE, INGEST_CB, void *);
#endif

#if 0
void* BinaryPluginHandle::CallPluginFunc(const char *func, va_list argList)
{
	if (pluginFuncTypeMap.find(func) == pluginFuncTypeMap.end())
	{
		logger->info("%s:%d: returning NULL", __FUNCTION__, __LINE__);
		return NULL;
	}

	void		(*pluginStartPtr)(PLUGIN_HANDLE);
	Reading		(*pluginPollPtr)(PLUGIN_HANDLE);
	void		(*pluginReconfigurePtr)(PLUGIN_HANDLE,
					        const std::string& newConfig);
	void		(*pluginShutdownPtr)(PLUGIN_HANDLE);
	void		(*pluginRegisterPtr)(PLUGIN_HANDLE, INGEST_CB, void *);

	switch(pluginFuncTypeMap.find(func)->second)
	{
		case PLUGIN_INIT:
			{
			pluginInitPtr = (PLUGIN_HANDLE (*)(const void *))
										ResolveSymbol("plugin_init");
			ConfigCategory *config = va_arg(argList, ConfigCategory*);
			void *rv = (*pluginInitPtr)(handle, config);
			return rv;
			}
			break;

		case PLUGIN_START:
			{
			pluginStartPtr = (void (*)(PLUGIN_HANDLE))
										ResolveSymbol("plugin_start");
			void *rv = (*pluginStartPtr)(handle);
			return;
			}
			break;

			
		case PLUGIN_POLL:
			{
			pluginPollPtr = (Reading (*)(PLUGIN_HANDLE))
										ResolveSymbol(handle, "plugin_poll");
			Reading rdng = (*pluginPollPtr)(handle);
			return ((void*) rdng);
			}
			break;
	}
	
	
}
#endif

PyObject* pModule;

PythonPluginHandle::PythonPluginHandle(const char *name, const char *_path)
{
	// Python 3.5 loaded filter module handle
	// pModule = NULL;

	string path(_path);
	
	// Python 3.5  script name
	std::size_t found = path.find_last_of("/");
	string pythonScript = path.substr(found + 1);
	string filtersPath = path.substr(0, found);
	//filtersPath = path.substr(0, filtersPath.find_last_of("/"));
	
	// Embedded Python 3.5 program name
	wchar_t *programName = Py_DecodeLocale(name, NULL);
    Py_SetProgramName(programName);
	PyMem_RawFree(programName);

	const char* foglampRootDir = getenv("FOGLAMP_ROOT");
	string foglampPythonDir = (string(foglampRootDir) + "/python");
	
	// Embedded Python 3.5 initialisation
    Py_Initialize();

	// Get FogLAMP Data dir
	//string filtersPath = getDataDir() + PYTHON_FILTERS_PATH;
	Logger::getLogger()->info("%s:%d: filtersPath=%s, pythonScript=%s", __FUNCTION__, __LINE__, filtersPath.c_str(), pythonScript.c_str());
	
	// Set Python path for embedded Python 3.5
	// Get current sys.path. borrowed reference
	PyObject* sysPath = PySys_GetObject((char *)"path");
	// Add FogLAMP python filters path
	PyList_Append(sysPath, PyUnicode_FromString((char *) filtersPath.c_str()));
	PyList_Append(sysPath, PyUnicode_FromString((char *) foglampPythonDir.c_str()));
	//PyObject* pPath = PyUnicode_DecodeFSDefault((char *)filtersPath.c_str());
	//PyList_Insert(sysPath, 0, pPath);
	// Remove temp object
	//Py_CLEAR(pPath);

	//sysPath = PySys_GetObject((char *)string("path").c_str());
	//Logger::getLogger()->info("%s:%d: sysPath=%s", __FUNCTION__, __LINE__, PyBytes_AsString(sysPath));
	//Py_CLEAR(sysPath);

	// 2) Import Python script
	pModule = PyImport_ImportModule(name);

	// Check whether the Python module has been imported
	if (!pModule)
	{
		// Failure
		if (PyErr_Occurred())
		{
			logErrorMessage();
		}
		Logger::getLogger()->fatal("PythonPluginHandle c'tor: cannot import Python 3.5 script "
					   "'%s' from '%s' : pythonScript=%s, filtersPath=%s",
					   name, _path,
					   pythonScript.c_str(),
					   filtersPath.c_str());
	}
	Logger::getLogger()->info("%s:%d: python module loaded successfully, pModule=%p", __FUNCTION__, __LINE__, pModule);

#if 1
 	PyObject* pFunc;
	pFunc = PyObject_GetAttrString(pModule, "plugin_info");
	if (!pFunc)
    {
		PRINT_FUNC;
        PyErr_Print();
    }
	PRINT_FUNC;
	Logger::getLogger()->info("c'tor: pFunc=%p", pFunc);

	if (!pFunc || !PyCallable_Check(pFunc))
	{
		PRINT_FUNC;
		// Failure
		if (PyErr_Occurred())
		{
			logErrorMessage();
		}
		PRINT_FUNC;

		Logger::getLogger()->fatal("Cannot find method plugin_info in loaded python module");
		Py_CLEAR(pFunc);

		return;
	}
	
	PRINT_FUNC;
	
	// - 2 - Call Python method passing an object
	PyObject* pReturn = PyObject_CallFunction(pFunc, NULL);

	PRINT_FUNC;

	PLUGIN_INFORMATION *info = NULL;

	// - 3 - Handle filter returned data
	if (!pReturn)
	{
		// Errors while getting result object
		Logger::getLogger()->error("Called python script method plugin_info : error while getting result object");

		// Errors while getting result object
		logErrorMessage();

		// Filter did nothing: just pass input data
		info = NULL;
	}
	else
	{
		PRINT_FUNC;
		
		// Get new set of readings from Python filter
		info = Py2C_PluginInfo(pReturn);
		
		// Remove pReturn object
		Py_CLEAR(pReturn);
	}
	if(info)
		Logger::getLogger()->info("plugin_handle: plugin_info(): info={name=%s, version=%s, options=%d, type=%s, interface=%s, config=%s}", 
					info->name, info->version, info->options, info->type, info->interface, info->config);

#endif
}

#if 0
void* PythonPluginHandle::openHandle(const char *)
{
	return NULL;
}
#endif

PythonPluginHandle::~PythonPluginHandle()
{
	// Decrement pModule reference count
	Py_CLEAR(pModule);
	// Decrement pFunc reference count
	// Py_CLEAR(info->pFunc);

	// Cleanup Python 3.5
	Py_Finalize();
}

#if 0
Reading		(*pluginPollPtr)(PLUGIN_HANDLE);
	void		(*pluginReconfigurePtr)(PLUGIN_HANDLE,
					        const std::string& newConfig);
	void		(*pluginShutdownPtr)(PLUGIN_HANDLE);
#endif

void *PythonPluginHandle::ResolveSymbol(const char *_sym)
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
	else
	{
		Logger::getLogger()->info("PythonPluginHandle::ResolveSymbol returning NULL for sym=%s", _sym);
		return NULL;
	}
#if 0
	else if (sym == "plugin_start")
		return (void *) plugin_start;
	else if (sym == "plugin_reconfigure")
		return (void *) plugin_reconfigure;
	else if (sym == "plugin_register_ingest")
		return (void *) plugin_register_ingest;
#endif
}

Reading* Py2C_getReading(PyObject *element)
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
						   "asset_code");
	// Get 'reading' value: borrowed reference.
	PyObject* reading = PyDict_GetItemString(element,
						 "reading");
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

	//Logger::getLogger()->info("plugin_poll_fn: asset_code=%s, reading is a python dict", PyUnicode_AsUTF8(assetCode));

	// Fetch all Datapoins in 'reading' dict			
	PyObject *dKey, *dValue;
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
		else
		{
			delete dataPoint;
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
		if (ts && PyLong_Check(ts))
		{
			// Set timestamp
			newReading->setTimestamp(PyLong_AsUnsignedLong(ts));
		}

		// Get 'user_ts' value: borrowed reference.
		PyObject* uts = PyDict_GetItemString(element, "user_ts");
		if (uts && PyLong_Check(uts))
		{
			// Set user timestamp
			newReading->setUserTimestamp(PyLong_AsUnsignedLong(uts));
		}

		// Get 'uuid' value: borrowed reference.
		PyObject* uuid = PyDict_GetItemString(element, "uuid");
		if (uuid && PyBytes_Check(uuid))
		{
			// Set uuid
			newReading->setUuid(PyUnicode_AsUTF8(uuid));
		}

		// Remove temp objects
		delete dataPoint;
	}
	return newReading;
}


Reading plugin_poll_fn(PLUGIN_HANDLE handle)
{
	PyObject* pFunc;
	//Logger::getLogger()->info("plugin_handle: plugin_poll(): pModule=%p, pFunc=%p", pModule, pFunc);
	PRINT_FUNC;
	
	// Fetch required method in loaded object
	pFunc = PyObject_GetAttrString(pModule, "plugin_poll");
	if (!pModule || !pFunc)
		Logger::getLogger()->info("plugin_handle: plugin_poll(): pModule=%p, pFunc=%p", pModule, pFunc);

	if (!pFunc || !PyCallable_Check(pFunc))
	{
		// Failure
		if (PyErr_Occurred())
		{
			logErrorMessage();
		}

		Logger::getLogger()->fatal("Cannot find method plugin_poll in loaded python module");
		Py_CLEAR(pFunc);

		return Reading("Invalid", NULL);
	}

	PRINT_FUNC;

	string *pluginHandleStr = (string *) handle;
	
	// - 2 - Call Python method passing an object
	PyObject* pReturn = PyObject_CallFunction(pFunc, "s", pluginHandleStr->c_str());

	PRINT_FUNC;

	// - 3 - Handle filter returned data
	if (!pReturn)
	{
		// Errors while getting result object
		Logger::getLogger()->error("Called python script method plugin_poll : error while getting result object");

		// Errors while getting result object
		logErrorMessage();

		return Reading("Invalid", NULL);
	}
	else
	{
		// Get plugin information from Python filter
		Reading *rdng = Py2C_getReading(pReturn);
		Logger::getLogger()->info("plugin_poll_fn: reading='%s'", rdng->toJSON().c_str());
		
		// Remove pReturn object
		Py_CLEAR(pReturn);
		Reading reading(*rdng);
		delete rdng;
		PRINT_FUNC;
		return reading;
	}
}


void plugin_shutdown_fn(PLUGIN_HANDLE handle)
{
	PyObject* pFunc;
	
	// Fetch required method in loaded object
	pFunc = PyObject_GetAttrString(pModule, "plugin_shutdown");
	if (!pModule || !pFunc)
		Logger::getLogger()->info("plugin_handle: plugin_shutdown(): pModule=%p, pFunc=%p", pModule, pFunc);

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

	PRINT_FUNC;

	string *pluginHandleStr = (string *) handle;
	
	// - 2 - Call Python method passing an object
	PyObject* pReturn = PyObject_CallFunction(pFunc, "s", pluginHandleStr->c_str());

	PRINT_FUNC;

	// - 3 - Handle filter returned data
	if (!pReturn)
	{
		// Errors while getting result object
		Logger::getLogger()->error("Called python script method plugin_shutdown : error while getting result object");

		// Errors while getting result object
		logErrorMessage();
	}
}

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

	PRINT_FUNC;

	Logger::getLogger()->info("plugin_handle: plugin_init(): config->toJSON()='%s'", config->toJSON().c_str());
	
	// - 2 - Call Python method passing an object
	PyObject* pReturn = PyObject_CallFunction(pFunc, "s", config->toJSON().c_str());

	PRINT_FUNC;

	// - 3 - Handle filter returned data
	if (!pReturn)
	{
		// Errors while getting result object
		Logger::getLogger()->error("Called python script method plugin_init : error while getting result object");

		// Errors while getting result object
		logErrorMessage();

		return NULL;
	}
	else
	{
		PRINT_FUNC;
		
		string *handleStr = new string(PyUnicode_AsUTF8(pReturn));

		Logger::getLogger()->info("plugin_handle: plugin_init(): got a valid handle from python plugin='%s'", handleStr->c_str());
		
		// Remove pReturn object
		Py_CLEAR(pReturn);

		return (void *) handleStr;
	}
}


void *PythonPluginHandle::GetInfo()
{
	Logger::getLogger()->info("PythonPluginHandle::GetInfo()");
	return (void *) plugin_info_fn;
}
	
PLUGIN_INFORMATION *plugin_info_fn()
{
	PyObject* pFunc;
	
	//if (pFunc == NULL)
	{
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
	}

	PRINT_FUNC;
	
	// - 2 - Call Python method passing an object
	PyObject* pReturn = PyObject_CallFunction(pFunc, NULL);

	PRINT_FUNC;

	PLUGIN_INFORMATION *info = NULL;

	// - 3 - Handle filter returned data
	if (!pReturn)
	{
		// Errors while getting result object
		Logger::getLogger()->error("Called python script method plugin_info : error while getting result object");

		// Errors while getting result object
		logErrorMessage();

		// Filter did nothing: just pass input data
		info = NULL;
	}
	else
	{
		PRINT_FUNC;
		
		// Get plugin information from Python filter
		info = Py2C_PluginInfo(pReturn);
		
		// Remove pReturn object
		Py_CLEAR(pReturn);
	}
	if(info)
		Logger::getLogger()->info("plugin_handle: plugin_info(): info={name=%s, version=%s, options=%d, type=%s, interface=%s, config=%s}", 
					info->name, info->version, info->options, info->type, info->interface, info->config);
	return info;
}

#define GET_PLUGIN_INFO_ELEM(elem) \
{ \
		PyObject* item = PyDict_GetItemString(element, #elem);\
		char * elem = new char [string(PyBytes_AsString(item)).length()+1];\
		std::strcpy (elem, string(PyBytes_AsString(item)).c_str());\
		info->elem = elem;\
}

/**
 * Get PLUGIN_INFORMATION structure filled from Python object
 *
 * @param pyRetVal	Python 3.5 Object (dict)
 * @return		Pointer to a new PLUGIN_INFORMATION structure
 *				or NULL in case of errors
 */
PLUGIN_INFORMATION *Py2C_PluginInfo(PyObject* pyRetVal)
{
	// Create returnable PLUGIN_INFORMATION structure
	PLUGIN_INFORMATION *info = new PLUGIN_INFORMATION;

	PyObject *dKey, *dValue;
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

static void logErrorMessage()
{
	Logger::getLogger()->info("%s:%d", __FUNCTION__, __LINE__);
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

