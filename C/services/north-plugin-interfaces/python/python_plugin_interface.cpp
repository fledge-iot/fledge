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

#if 0
def plugin_send(handle, readings):
    _LOGGER.info("plugin_send")

    # Create loop object
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Just pass a fake id as thrird parameter
    coroObj = _plugin.plugin_send(handle, readings, "000001")

    # Set coroutine to wait for
    futures = [coroObj]
    done, result = loop.run_until_complete(asyncio.wait(futures))

    numSent = 0 
    for t in done:
        # Fetch done task result
        retCode, lastId, numSent = t.result()

    return numSent
#endif

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
			PyObject* pReturn = PyObject_CallObject(method, Py_BuildValue("OOO", handle, readingsList, plugin_send_module_func));
            Logger::getLogger()->info("%s:%d, pReturn=%p", __FUNCTION__, __LINE__, pReturn);
			if (pReturn != NULL)
			{
				if(PyLong_Check(pReturn))
				{
					numSent = (long)PyLong_AsUnsignedLongMask(pReturn);
					Logger::getLogger()->info("numSent=%d", numSent);
				}
				else
					Logger::getLogger()->info("plugin_send_wrapper() didn't return a number, returned value is of type %s", (Py_TYPE(pReturn))->tp_name);
				
				// Py_CLEAR(tmp);
			}
            else
            {
                Logger::getLogger()->info("%s:%d: pReturn is NULL", __FUNCTION__, __LINE__);
                if (PyErr_Occurred())
        		{
        			logErrorMessage();
        		}
            }
            
			Py_CLEAR(pReturn);
		}
		Py_CLEAR(method);
	}
        
	// Reset error
	PyErr_Clear();

	// Remove references
	//Py_CLEAR(type);
	//Py_CLEAR(value);
	//Py_CLEAR(traceback);
	Py_CLEAR(mod);

    return numSent;
}

#if 0
const char *call_plugin_send_coroutine(PyObject *plugin_send_module_func, PyObject *handle, PyObject *readingsList)
{
PyObject *rval;
va_list ap;
PyObject *mod, *method, *new_event_loop, *loop, *set_event_loop_method;

    Logger::getLogger()->info("%s:%d", __FUNCTION__, __LINE__);

	PyGILState_STATE state = PyGILState_Ensure();
    Logger::getLogger()->info("%s:%d", __FUNCTION__, __LINE__);
	if ((mod = PyImport_ImportModule("asyncio")) != NULL)
	{
        Logger::getLogger()->info("%s:%d", __FUNCTION__, __LINE__);
        if ((new_event_loop = PyObject_GetAttrString(mod, "new_event_loop")) != NULL)
		{
            Logger::getLogger()->info("%s:%d", __FUNCTION__, __LINE__);
            // loop = asyncio.new_event_loop()
            PyObject *args = PyTuple_New(0);
            Logger::getLogger()->info("%s:%d", __FUNCTION__, __LINE__);
            loop = PyObject_Call(new_event_loop, args, NULL);
            Logger::getLogger()->info("%s:%d", __FUNCTION__, __LINE__);
            if (loop == NULL)
			{
                Logger::getLogger()->info("%s:%d", __FUNCTION__, __LINE__);
				if (PyErr_Occurred())
				{
					logErrorMessage();
                    return NULL;
				}
			}
            else
                Logger::getLogger()->info("%s:%d, new_event_loop created, loop type=%s", __FUNCTION__, __LINE__, (Py_TYPE(loop))->tp_name);

            // TODO: free python objects that are no longer required
            Logger::getLogger()->info("%s:%d", __FUNCTION__, __LINE__);
            
            set_event_loop_method = PyObject_GetAttrString(mod, "set_event_loop");
            Logger::getLogger()->info("%s:%d", __FUNCTION__, __LINE__);
            args = PyTuple_New(1);
            PyObject *pValue = Py_BuildValue("O", loop);
            PyTuple_SetItem(args, 0, pValue);
            Logger::getLogger()->info("%s:%d", __FUNCTION__, __LINE__);

            // asyncio.set_event_loop(loop)
			rval = PyObject_Call(set_event_loop_method, args, NULL);
            Logger::getLogger()->info("%s:%d", __FUNCTION__, __LINE__);
			if (rval == NULL)
			{
				if (PyErr_Occurred())
				{
					logErrorMessage();
                    return NULL;
				}
			}
            else
                Logger::getLogger()->info("%s:%d, set_event_loop called succeeded, rval type=%s", __FUNCTION__, __LINE__, (Py_TYPE(rval))->tp_name);

            // coroObj = _plugin.plugin_send(handle, readings, "000001")
            args = PyTuple_New(3);
                
            PyTuple_SetItem(args, 0, Py_BuildValue("O", handle));
            PyTuple_SetItem(args, 1, Py_BuildValue("O", readingsList));
            PyTuple_SetItem(args, 2, Py_BuildValue("s", "000001"));
    
			PyObject *coroObj = PyObject_Call(plugin_send_module_func, args, NULL);
            Logger::getLogger()->info("%s:%d", __FUNCTION__, __LINE__);
			if (coroObj == NULL)
			{
				if (PyErr_Occurred())
				{
					logErrorMessage();
                    return NULL;
				}
			}
            else
                Logger::getLogger()->info("%s:%d, plugin's plugin_send called successfully, coroObj type is %s", 
                                                                __FUNCTION__, __LINE__, (Py_TYPE(coroObj))->tp_name);

            // futures = [coroObj]
            PyObject *futures = PyList_New(1);
            PyList_SetItem(futures, 0, Py_BuildValue("O", coroObj));
            Logger::getLogger()->info("%s:%d", __FUNCTION__, __LINE__);

            // coroutine = asyncio.wait(futures)
            PyObject *wait, *coroutine;
            args = PyTuple_New(1);
            PyTuple_SetItem(args, 0, futures);
            Logger::getLogger()->info("%s:%d", __FUNCTION__, __LINE__);
            
            if ((wait = PyObject_GetAttrString(mod, "wait")) != NULL)
            {
                Logger::getLogger()->info("%s:%d", __FUNCTION__, __LINE__);
                coroutine = PyObject_Call(wait, args, NULL);
                Logger::getLogger()->info("%s:%d", __FUNCTION__, __LINE__);
                if (coroutine == NULL)
                {
                    if (PyErr_Occurred())
                    {
                        logErrorMessage();
                        return NULL;
                    }
                }
                else
                    Logger::getLogger()->info("%s:%d, coroutine with futures created, coroutine type=%s", 
                                                        __FUNCTION__, __LINE__, (Py_TYPE(coroutine))->tp_name);
                Logger::getLogger()->info("%s:%d", __FUNCTION__, __LINE__);
            }
            else
            {
                Logger::getLogger()->info("%s:%d, wait is NULL", __FUNCTION__, __LINE__);
            }

            Logger::getLogger()->info("%s:%d", __FUNCTION__, __LINE__);

            // done, result = loop.run_until_complete(asyncio.wait(futures))
            PyObject *run_until_complete, *done, *result;
            if ((run_until_complete = PyObject_GetAttrString(loop, "run_until_complete")) != NULL)
            {
                args = PyTuple_New(1);
                PyTuple_SetItem(args, 0, coroutine);
                
                rval = PyObject_Call(run_until_complete, args, NULL);
                if (rval == NULL)
                {
                    if (PyErr_Occurred())
                    {
                        logErrorMessage();
                        return NULL;
                    }
                }
                else
                {
                    Logger::getLogger()->info("%s:%d, loop.run_until_complete done, rval type=%s", 
                                                        __FUNCTION__, __LINE__, (Py_TYPE(rval))->tp_name);
                    size_t sz = (size_t) PyTuple_Size(rval);
                    Logger::getLogger()->info("%s:%d", __FUNCTION__, __LINE__);
                    done = PyTuple_GetItem(args, 0);
                    Logger::getLogger()->info("%s:%d", __FUNCTION__, __LINE__);
                    result = PyTuple_GetItem(args, 1);
                    Logger::getLogger()->info("%s:%d, tuple size=%d", __FUNCTION__, __LINE__, sz);

                    if (done)
                        Logger::getLogger()->info("%s:%d, tuple size=%d, done type=%s", __FUNCTION__, __LINE__, 
                                                      sz, (Py_TYPE(done))->tp_name);
                    else
                        Logger::getLogger()->info("%s:%d, tuple size=%d, done is NULL", __FUNCTION__, __LINE__, sz);
                        
                    if (result)
                        Logger::getLogger()->info("%s:%d, tuple size=%d, result type=%s", __FUNCTION__, __LINE__, 
                                                      sz, (Py_TYPE(result))->tp_name);
                    else
                        Logger::getLogger()->info("%s:%d, tuple size=%d, result is NULL", __FUNCTION__, __LINE__, sz);
                    
                }
            }
            else
            {
                Logger::getLogger()->info("%s:%d, loop.run_until_complete returned NULL", __FUNCTION__, __LINE__);
            }
#if 0
            PyObject *done=NULL, *result=NULL;
            if (!PyArg_ParseTuple(rval, "OO", done, result))
            {
                logErrorMessage();
                Logger::getLogger()->info("%s:%d: (Py_TYPE(done))->tp_name=%s, (Py_TYPE(result))->tp_name=%s", 
                                           __FUNCTION__, __LINE__, (Py_TYPE(done))->tp_name, (Py_TYPE(result))->tp_name);
                Logger::getLogger()->error("%s:%d: Cannot parse return values of 'plugin_send' for north plugin", __FUNCTION__, __LINE__);
                //numSent=0;
            }
            else
            {
                Logger::getLogger()->info("%s:%d: (Py_TYPE(done))->tp_name=%s, (Py_TYPE(result))->tp_name=%s", 
                                             __FUNCTION__, __LINE__, (Py_TYPE(done))->tp_name, (Py_TYPE(result))->tp_name);
                Logger::getLogger()->info("%s:%d: retCode=%s, lastId=%d, numSent=%d", __FUNCTION__, __LINE__, retCode?"TRUE":"FALSE", lastId, numSent);
            }
#endif
            unsigned int numSent = 0;
            PyObject *m = PyImport_AddModule("__main__");
            Logger::getLogger()->info("%s:%d", __FUNCTION__, __LINE__);
            args = PyTuple_New(1);
            PyTuple_SetItem(args, 0, done);
            Logger::getLogger()->info("%s:%d", __FUNCTION__, __LINE__);
            PyObject *builtins = PyEval_GetBuiltins();
            Logger::getLogger()->info("%s:%d", __FUNCTION__, __LINE__);
            PyObject *_next = NULL;
            if ((_next = PyDict_GetItemString(builtins , "next")) != NULL)
            {
                Logger::getLogger()->info("%s:%d: _next=%p, PyCallable_Check(_next)=%s", 
                                            __FUNCTION__, __LINE__, _next, PyCallable_Check(_next)?"TRUE":"FALSE");
                
                //PyObject *iterator = PyObject_GetIter(done);
                Logger::getLogger()->info("%s:%d", __FUNCTION__, __LINE__);
                
                /*if (iterator == NULL) 
                {
                   Logger::getLogger()->info("%s:%d: Could not get iterator for 'done'", __FUNCTION__, __LINE__);
                }
                else */
                {
                    PyObject *item = NULL;
                    while((item = PyIter_Next(done)) != NULL)
                    {
                        /*
                        Logger::getLogger()->info("%s:%d", __FUNCTION__, __LINE__);
                        // rval = PyObject_Call(_next, args, NULL);
                        rval = PyEval_CallFunction(_next, "(O)", done);
                        item = PyIter_Next(done);
                        */
                        Logger::getLogger()->info("%s:%d, next(done/generator) returned, item rval type=%s",
                                                            __FUNCTION__, __LINE__, (Py_TYPE(item))->tp_name);
                        Py_DECREF(item);
                    }
                    Logger::getLogger()->info("%s:%d", __FUNCTION__, __LINE__);
                    //Py_DECREF(iterator);
                }
            }
            else
                Logger::getLogger()->info("%s:%d", __FUNCTION__, __LINE__);

            Logger::getLogger()->info("%s:%d", __FUNCTION__, __LINE__);
			// Py_CLEAR(method);
            // Logger::getLogger()->info("%s:%d", __FUNCTION__, __LINE__);
		}
		else
		{
			Logger::getLogger()->fatal("Method 'new_event_loop' not found");
		}
        Logger::getLogger()->info("%s:%d", __FUNCTION__, __LINE__);
		// Remove references
		Py_CLEAR(mod);
	}
	else
	{
		Logger::getLogger()->fatal("Failed to import module");
	}
    Logger::getLogger()->info("%s:%d", __FUNCTION__, __LINE__);

bail_out:
	// Reset error
	PyErr_Clear();

	PyGILState_Release(state);

    Logger::getLogger()->info("%s:%d", __FUNCTION__, __LINE__);

    const char *retVal = PyUnicode_AsUTF8(rval);
    Logger::getLogger()->info("json_dumps3(): retVal=%s", retVal);
    
	return retVal;
}
#endif


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

	string fledgePythonDir;
    
	string fledgeRootDir(getenv("FLEDGE_ROOT"));
	fledgePythonDir = fledgeRootDir + "/python";
    
	string northRootPath = fledgePythonDir + string(R"(/fledge/plugins/north/)") + string(pluginName);
    Logger::getLogger()->info("%s:%d:, northRootPath=%s", __FUNCTION__, __LINE__, northRootPath.c_str());
    
    // Embedded Python 3.5 program name
	wchar_t *programName = Py_DecodeLocale(pluginName, NULL);
	Py_SetProgramName(programName);
	PyMem_RawFree(programName);

    // string name(string(PLUGIN_TYPE_NORTH) + string(SHIM_SCRIPT_POSTFIX));
    // Logger::getLogger()->info("%s:%d:, name=%s", __FUNCTION__, __LINE__, name);
	PythonRuntime::getPythonRuntime();

    Logger::getLogger()->info("%s:%d", __FUNCTION__, __LINE__);
    
	// Acquire GIL
	PyGILState_STATE state = PyGILState_Ensure();

    Logger::getLogger()->info("NorthPlugin %s:%d: "
				   "northRootPath=%s, fledgePythonDir=%s, plugin '%s'",
				   __FUNCTION__,
				   __LINE__,
				   northRootPath.c_str(),
				   fledgePythonDir.c_str(),
				   pluginName);

        // string northDir = fledgePythonDir + R"(fledge/plugins/north)";
	// Set Python path for embedded Python 3.x
	// Get current sys.path - borrowed reference
	PyObject* sysPath = PySys_GetObject((char *)"path");
	PyList_Append(sysPath, PyUnicode_FromString((char *) northRootPath.c_str()));
	PyList_Append(sysPath, PyUnicode_FromString((char *) fledgePythonDir.c_str()));

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
		Logger::getLogger()->warn("Cannot find 'plugin_start' method "
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

		Logger::getLogger()->warn("Cannot call method 'plugin_start' "
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

		Logger::getLogger()->fatal("Cannot call method plugin_send"
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
    PyObject* readingsList = pyReadingSet->toPython();
    PyObject* objectsRepresentation = PyObject_Repr(readingsList);
    const char* s = PyUnicode_AsUTF8(objectsRepresentation);
    Logger::getLogger()->info("C2Py: plugin_send_fn():L%d: filtered readings to send = %s", __LINE__, s);
    Py_CLEAR(objectsRepresentation);
    
    // PyObject* handleObj = PyCapsule_New((void *)handle, NULL, NULL);
    data = call_plugin_send_coroutine(pFunc, handle, readingsList);
    
	// Remove readings list object
	Py_CLEAR(readingsList);

	// Remove result object
	// Py_CLEAR(handleObj);

	// Release GIL
	PyGILState_Release(state);

	// Return the number of readings sent
	return data;
}

};

