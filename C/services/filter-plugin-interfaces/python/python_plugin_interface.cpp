/*
 * FogLAMP filter plugin interface related
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
#include <reading_set.h>
#include <mutex>
#include <plugin_handle.h>
#include <Python.h>

#include <python_plugin_common_interface.h>
#include <reading_set.h>

#define SHIM_SCRIPT_REL_PATH  "/python/foglamp/plugins/common/shim/"
#define SHIM_SCRIPT_NAME "filter_shim"

using namespace std;

extern "C" {

// This is a C++ ReadingSet class instance passed through
typedef ReadingSet READINGSET;
// Data handle passed to function pointer
typedef void OUTPUT_HANDLE;
// Function pointer called by "plugin_ingest" plugin method
typedef void (*OUTPUT_STREAM)(OUTPUT_HANDLE *, READINGSET *);

extern PLUGIN_INFORMATION *Py2C_PluginInfo(PyObject *);
extern void logErrorMessage();
extern PLUGIN_INFORMATION *plugin_info_fn();
extern void plugin_shutdown_fn(PLUGIN_HANDLE);
extern PyObject* createReadingsList(const vector<Reading *>& readings);

/**
 * Function to invoke 'plugin_reconfigure' function in python plugin
 *
 * @param    handle     The plugin handle from plugin_init_fn
 * @param    config     The new configuration, as string
 */
static void filter_plugin_reconfigure_fn(PLUGIN_HANDLE handle,
					 const std::string& config)
{
	if (!pythonModules)
	{
		Logger::getLogger()->error("pythonModules map is NULL "
					   "in plugin_reconfigure_fn, plugin '%s'",
					   gPluginName.c_str());
		return;
	}

	// Look for Python module for gPluginName key
	auto it = pythonModules->find(gPluginName);
	if (it == pythonModules->end() ||
	    !it->second)
	{
		Logger::getLogger()->fatal("plugin_handle: plugin_reconfigure(): "
					   "pModule is NULL for plugin '%s'",
					   gPluginName.c_str());
		return;
	}

	std::mutex mtx;
	PyObject* pFunc;
	lock_guard<mutex> guard(mtx);
	PyGILState_STATE state = PyGILState_Ensure();

	Logger::getLogger()->debug("plugin_handle: plugin_reconfigure(): pModule=%p, *handle=%p, plugin '%s'",
				   it->second,
				   handle,
				   gPluginName.c_str());

	// Fetch required method in loaded object
	pFunc = PyObject_GetAttrString(it->second, "plugin_reconfigure");
	if (!pFunc)
	{
		Logger::getLogger()->fatal("Cannot find method 'plugin_reconfigure' "
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

		Logger::getLogger()->fatal("Cannot call method plugin_reconfigure "
					   "in loaded python module '%s'",
					   gPluginName.c_str());
		Py_CLEAR(pFunc);

		PyGILState_Release(state);
		return;
	}

	Logger::getLogger()->debug("plugin_reconfigure with %s", config.c_str());

	// Call Python method passing an object and a C string
	PyObject* pReturn = PyObject_CallFunction(pFunc,
						  "Os",
						  handle,
						  config.c_str());

	Py_CLEAR(pFunc);

	// Handle returned data
	if (!pReturn)
	{
		Logger::getLogger()->error("Called python script method plugin_reconfigure "
					    ": error while getting result object, plugin '%s'",
					   gPluginName.c_str());
		logErrorMessage();
		//*handle = NULL; // not sure if this should be treated as unrecoverable failure on python plugin side
	}
	else
	{
		// Save curreent handle
		PyObject* tmp = (PyObject*)handle;
		// Create a new handle
		handle = PyObject_Init(pReturn, Py_TYPE(pReturn));
		// Remove old handle
		Py_CLEAR(tmp);

		Logger::getLogger()->debug("plugin_handle: plugin_reconfigure(): "
					   "got updated handle from python plugin=%p, plugin '%s'",
					   handle,
					   gPluginName.c_str());
	}

	PyGILState_Release(state);
}

/**
 * Ingest data into filters chain
 *
 * @param    handle     The plugin handle returned from plugin_init
 * @param    data       The ReadingSet data to filter
 */
void filter_plugin_ingest_fn(PLUGIN_HANDLE handle, READINGSET *data)
{
	if (!pythonModules)
	{
		Logger::getLogger()->error("pythonModules map is NULL "
					   "in filter_plugin_ingest_fn plugin '%s'",
					   gPluginName.c_str());
		return;
	}

	auto it = pythonModules->find(gPluginName);
	if (it == pythonModules->end() ||
	    !it->second)
	{
		Logger::getLogger()->fatal("plugin_handle: plugin_ingest(): "
					   "pModule is NULL for plugin '%s'",
					   gPluginName.c_str());
		return;
	}
	PyObject* pFunc;
	PyGILState_STATE state = PyGILState_Ensure();
	// Fetch required method in loaded object
	pFunc = PyObject_GetAttrString(it->second, "plugin_ingest");
	if (!pFunc)
	{
		Logger::getLogger()->fatal("Cannot find 'plugin_ingest' "
					   "method in loaded python module '%s'",
					   gPluginName.c_str());
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
					   gPluginName.c_str());
		Py_CLEAR(pFunc);

		PyGILState_Release(state);
		return;
	}

	// Create a dict of readings
	// - 1 - Create Python list of dicts as input to the filter
	PyObject* readingsList =
		createReadingsList(((ReadingSet *)data)->getAllReadings());

	PyObject* pReturn = PyObject_CallFunction(pFunc,
						  "OO",
						  handle,
						  readingsList);
	Py_CLEAR(pFunc);
	// Remove input data
	delete (ReadingSet *)data;
	data = NULL;

	// Handle returned data
	if (!pReturn)
	{
		Py_CLEAR(readingsList);
		Logger::getLogger()->error("Called python script method plugin_ingest "
					   ": error while getting result object, plugin '%s'",
					   gPluginName.c_str());
		logErrorMessage();
	}
	else
	{
		Logger::getLogger()->debug("plugin_handle: plugin_ingest: "
					   "got result object '%p', plugin '%s'",
					   pReturn,
					   gPluginName.c_str());
	}
	Py_CLEAR(pReturn);
	PyGILState_Release(state);
}

/**
 * Initialise the plugin, called to get the plugin handle and setup the
 * output handle that will be passed to the output stream. The output stream
 * is merely a function pointer that is called with the output handle and
 * the new set of readings generated by the plugin.
 *     (*output)(outHandle, readings);
 * Note that the plugin may not call the output stream if the result of
 * the filtering is that no readings are to be sent onwards in the chain.
 * This allows the plugin to discard data or to buffer it for aggregation
 * with data that follows in subsequent calls
 *
 * @param config	The configuration category for the filter
 * @param outHandle	A handle that will be passed to the output stream
 * @param output	The output stream (function pointer) to which data is passed
 * @return		An opaque handle that is used in all subsequent calls to the plugin
 */
PLUGIN_HANDLE filter_plugin_init_fn(ConfigCategory* config,
			  OUTPUT_HANDLE *outHandle,
			  OUTPUT_STREAM output)
{
	if (!pythonModules)
	{
		Logger::getLogger()->error("pythonModules map is NULL "
					   "in filter_plugin_init_fn, plugin '%s'",
					   gPluginName.c_str());
		return NULL;
	}

	auto it = pythonModules->find(gPluginName);
	if (it == pythonModules->end() ||
	    !it->second)
        {
                Logger::getLogger()->fatal("plugin_handle: plugin_init(): "
                                           "pModule is NULL for plugin '%s'",
                                           gPluginName.c_str());
                return NULL;
        }
        PyObject* pFunc;
        PyGILState_STATE state = PyGILState_Ensure();

        // Fetch required method in loaded object
        pFunc = PyObject_GetAttrString(it->second, "plugin_init");
        if (!pFunc)
        {
                Logger::getLogger()->fatal("Cannot find 'plugin_init' "
                                           "method in loaded python module '%s'",
                                           gPluginName.c_str());
        }

        if (!pFunc || !PyCallable_Check(pFunc))
        {
                // Failure
                if (PyErr_Occurred())
                {
                        logErrorMessage();
                }

                Logger::getLogger()->fatal("Cannot call method plugin_init "
                                           "in loaded python module '%s'",
                                           gPluginName.c_str());
                Py_CLEAR(pFunc);

                PyGILState_Release(state);
                return NULL;
        }

        // Call Python method passing an object
        PyObject* ingest_fn = PyCapsule_New((void *)output, NULL, NULL);
        PyObject* ingest_ref = PyCapsule_New((void *)outHandle, NULL, NULL);
        PyObject* pReturn = PyObject_CallFunction(pFunc,
						  "sOO",
						  config->itemsToJSON().c_str(),
						  ingest_ref,
						  ingest_fn);

        Py_CLEAR(pFunc);
        Py_CLEAR(ingest_ref);
        Py_CLEAR(ingest_fn);


        // Handle returned data
        if (!pReturn)
        {
                Logger::getLogger()->error("Called python script method plugin_init "
                                           ": error while getting result object, plugin '%s'",
                                           gPluginName.c_str());
                logErrorMessage();
        }
        else
        {
                Logger::getLogger()->debug("plugin_handle: filter_plugin_init(): "
                                           "got result object '%p', plugin '%s'",
                                           pReturn,
                                           gPluginName.c_str());
        }
        PyGILState_Release(state);

	return (PLUGIN_HANDLE)pReturn;
}

/**
 * Constructor for PythonPluginHandle
 *    - Load python interpreter
 *    - Set sys.path and sys.argv
 *    - Import shim layer script and pass plugin name in argv[1]
 *
 * @param    pluginName         The plugin name to load
 * @param    pluginPathName     The plugin pathname
 */
void *PluginInterfaceInit(const char *pluginName, const char * pluginPathName)
{
	// Set plugin name, also for methods in common-plugin-interfaces/python
        gPluginName = pluginName;
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
	if (!Py_IsInitialized())
	{
		Py_Initialize();
		PyEval_InitThreads();
		PyThreadState* save = PyEval_SaveThread(); // release Python GIT
	}

        PyGILState_STATE state = PyGILState_Ensure();

        Logger::getLogger()->debug("SouthPlugin PythonInterface %s:%d: "
                                   "shimLayerPath=%s, foglampPythonDir=%s, plugin '%s'",
                                   __FUNCTION__,
                                   __LINE__,
                                   shimLayerPath.c_str(),
                                   foglampPythonDir.c_str(),
                                   gPluginName.c_str());

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
                                           gPluginName.c_str());
        }
        else
        {
		std::pair<std::map<string, PyObject*>::iterator, bool> ret;
		if (pythonModules)
		{
			// Add element
			ret = pythonModules->insert(pair<string, PyObject*>(string(pluginName), pModule));
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
                	                           gPluginName.c_str());
			Py_CLEAR(pModule);
			return NULL;
		}
		else
		{
                	Logger::getLogger()->debug("%s:%d: python module loaded successfully, pModule=%p, plugin '%s'",
                        	                   __FUNCTION__,
                                	           __LINE__,
                                        	   pModule,
                	                           gPluginName.c_str());
		}
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
		return (void *) filter_plugin_init_fn;
	else if (!sym.compare("plugin_shutdown"))
		return (void *) plugin_shutdown_fn;
	else if (!sym.compare("plugin_reconfigure"))
		return (void *) filter_plugin_reconfigure_fn;
	else if (!sym.compare("plugin_ingest"))
		return (void *) filter_plugin_ingest_fn;
	else if (!sym.compare("plugin_start"))
	{
		Logger::getLogger()->warn("FilterPluginInterface currently "
					  "does not support 'plugin_start'");
		return NULL;
	}
	else
	{
		Logger::getLogger()->fatal("FilterPluginInterfaceResolveSymbol can not find symbol '%s' "
					   "in the Filter Python plugin interface library, "
					   "loaded plugin '%s'",
					   _sym,
					   gPluginName.c_str());
		return NULL;
	}
}
}; // End of extern C
