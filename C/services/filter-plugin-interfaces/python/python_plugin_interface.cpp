/*
 * Fledge filter plugin interface related
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
#include <pyruntime.h>
#include <Python.h>

#include <python_plugin_common_interface.h>
#include <reading_set.h>
#include <filter_plugin.h>
#include <pythonreadingset.h>

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


/**
 * Function to invoke 'plugin_reconfigure' function in python plugin
 *
 * @param    handle     The plugin handle from plugin_init_fn
 * @param    config     The new configuration, as string
 */
static void filter_plugin_reconfigure_fn(PLUGIN_HANDLE handle,
					 const std::string& config)
{
	if (!handle)
	{
		Logger::getLogger()->fatal("plugin_handle: filter_plugin_reconfigure_fn(): "
					   "handle is NULL");
		return;
	}

	if (!pythonHandles)
	{
		// Plugin name can not be logged here
		Logger::getLogger()->error("pythonHandles map is NULL "
					   "in filter_plugin_reconfigure_fn");
		return;
	}

	// Look for Python module, handle is the key
	auto it = pythonHandles->find(handle);
	if (it == pythonHandles->end() ||
	    !it->second)
	{
		// Plugin name can not be logged here
		Logger::getLogger()->fatal("filter_plugin_reconfigure_fn(): "
					   "pModule is NULL, handle %p",
					   handle);
		return;
	}

        // We have plugin name
        string pName = it->second->m_name;

	std::mutex mtx;
	PyObject* pFunc;
	lock_guard<mutex> guard(mtx);
	PyGILState_STATE state = PyGILState_Ensure();

	Logger::getLogger()->debug("plugin_handle: plugin_reconfigure(): "
				   "pModule=%p, *handle=%p, plugin '%s'",
				   it->second->m_module,
				   handle,
				   pName.c_str());

	Logger::getLogger()->debug("%s:%d: calling set_loglevel_in_python_module(), loglevel=%s", __FUNCTION__, __LINE__, Logger::getLogger()->getMinLevel().c_str());
	if(config.compare("logLevel") == 0)
	{
		set_loglevel_in_python_module(it->second->m_module, it->second->m_name+" filter_plugin_reconf");
		PyGILState_Release(state);
		return;
	}
	
	// Fetch required method in loaded object
	pFunc = PyObject_GetAttrString(it->second->m_module, "plugin_reconfigure");
	if (!pFunc)
	{
		Logger::getLogger()->fatal("Cannot find method 'plugin_reconfigure' "
					   "in loaded python module '%s'",
					   pName.c_str());
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

		Logger::getLogger()->fatal("Cannot call method plugin_reconfigure "
					   "in loaded python module '%s'",
					   pName.c_str());
		Py_CLEAR(pFunc);

		PyGILState_Release(state);
		return;
	}

	Logger::getLogger()->debug("plugin_reconfigure with %s", config.c_str());

	PyObject *config_dict = json_loads(config.c_str());

	// Call Python method passing an object and JSON config dict
	PyObject* pReturn = PyObject_CallFunction(pFunc,
						  "OO",
						  handle,
						  config_dict);

	Py_CLEAR(pFunc);

	// Handle returned data
	if (!pReturn)
	{
		Logger::getLogger()->error("Called python script method plugin_reconfigure "
					   ": error while getting result object, plugin '%s'",
					   pName.c_str());
		logErrorMessage();
	}
	else
	{
        Logger::getLogger()->info("%s:%d: Py_TYPE(pReturn)->tp_name=%s", __FUNCTION__, __LINE__, Py_TYPE(pReturn)->tp_name);
		PyObject* tmp = (PyObject *)handle;
		// Check current handle is Dict and pReturn is a Dict too
		if (PyDict_Check(tmp) && PyDict_Check(pReturn))
		{
			// Clear Dict content
			PyDict_Clear(tmp);
			// Populate handle Dict with new data in pReturn
			PyDict_Update(tmp, pReturn);
			// Remove pReturn ojbect
			Py_CLEAR(pReturn);

			Logger::getLogger()->debug("plugin_handle: plugin_reconfigure(): "
						   "got updated handle from python plugin=%p, plugin '%s'",
						   handle,
						   pName.c_str());
		}
		else
		{
			 Logger::getLogger()->error("plugin_handle: plugin_reconfigure(): "
						    "got object type '%s' instead of Python Dict, "
						    "python plugin=%p, plugin '%s'",
						    Py_TYPE(pReturn)->tp_name,
					   	    handle,
					  	    pName.c_str());
		}
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
	if (!handle)
	{
		Logger::getLogger()->fatal("plugin_handle: filter_plugin_ingest_fn(): "
					   "handle is NULL");
		return;
	}

	if (!pythonHandles)
	{
		// Plugin name can not be logged here
		Logger::getLogger()->error("pythonHandles map is NULL "
					   "in filter_plugin_ingest_fn");
		return;
	}

	auto it = pythonHandles->find(handle);
	if (it == pythonHandles->end() ||
	    !it->second)
	{
		// Plugin name can not be logged here
		Logger::getLogger()->fatal("plugin_handle: plugin_ingest(): "
					   "pModule is NULL");
		return;
	}

	// We have plugin name
	string pName = it->second->m_name;

	PyObject* pFunc;
	PyGILState_STATE state = PyGILState_Ensure();

	// Fetch required method in loaded object
	pFunc = PyObject_GetAttrString(it->second->m_module, "plugin_ingest");
	if (!pFunc)
	{
		Logger::getLogger()->fatal("Cannot find 'plugin_ingest' "
					   "method in loaded python module '%s'",
					   pName.c_str());
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

		Logger::getLogger()->fatal("Cannot call method plugin_ingest"
					   "in loaded python module '%s'",
					   pName.c_str());
		Py_CLEAR(pFunc);

		PyGILState_Release(state);
		return;
	}

	// Call asset tracker
	// int i=0;
	vector<Reading *>* readings = ((ReadingSet *)data)->getAllReadingsPtr();
	for (vector<Reading *>::const_iterator elem = readings->begin();
						      elem != readings->end();
						      ++elem)
	{
		// Logger::getLogger()->debug("Reading %d: %s", i++, (*elem)->toJSON().c_str());
		AssetTracker* atr = AssetTracker::getAssetTracker();
		if (atr)
		{
			AssetTracker::getAssetTracker()->addAssetTrackingTuple(it->second->getCategoryName(),
										(*elem)->getAssetName(),
										string("Filter"));
		}
	}

	Logger::getLogger()->debug("C2Py: filter_plugin_ingest_fn():L%d: data->getCount()=%d", __LINE__, data->getCount());
	
	// Create a readingList of readings to be filtered
	PythonReadingSet *pyReadingSet = (PythonReadingSet *) data;
	PyObject* readingsList = pyReadingSet->toPython();

	PyObject* pReturn = PyObject_CallFunction(pFunc,
						  "OO",
						  handle,
						  readingsList);
	Py_CLEAR(pFunc);

	// Handle returned data
	if (!pReturn)
	{
		Logger::getLogger()->error("Called python script method plugin_ingest "
					   ": error while getting result object, plugin '%s'",
					   pName.c_str());
		logErrorMessage();
	}

	data->removeAll();
	delete data;

#if 0
	PythonReadingSet *filteredReadingSet = NULL;
	if (pReturn)
	{
		// Check we have a list of readings
		if (PyList_Check(readingsList))
		{
			try
			{
				// Create ReadingSet from Python reading list
				filteredReadingSet = new PythonReadingSet(readingsList);

				// Remove input data
				data->removeAll();

				// Append filtered readings;  append will empty the passed reading set as well
				data->append(filteredReadingSet);

				delete filteredReadingSet;
				filteredReadingSet = NULL;
			}
			catch (std::exception e)
			{
				Logger::getLogger()->warn("Unable to create a PythonReadingSet, error: %s", e.what());
				filteredReadingSet = NULL;
			}
		}
		else
		{
			Logger::getLogger()->error("Filter did not return a Python List "
						   "but object type %s",
						   Py_TYPE(readingsList)->tp_name);
		}
	}
#endif
	
	// Remove readings to dict
	Py_CLEAR(readingsList);
	// Remove CallFunction result
	Py_CLEAR(pReturn);

	// Release GIL
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
	// Get pluginName
	string pName = config->getValue("plugin");

	Logger::getLogger()->info("filter_plugin_init_fn(): pName=%s", pName.c_str());

	if (!pythonModules)
	{
		Logger::getLogger()->error("pythonModules map is NULL "
					   "in filter_plugin_init_fn, plugin '%s'",
					   pName.c_str());
		return NULL;
	}

	bool loadModule = false;   // whether module is already loaded
	bool reloadModule = false;  // whether module is to be loaded again
	bool pythonInitState = false;
	PythonModule *module = NULL;

	// Check whether plugin pName has been already loaded
	for (auto h = pythonHandles->begin();
                  h != pythonHandles->end(); ++h)
	{
		if (h->second->m_name.compare(pName) == 0)
		{
			Logger::getLogger()->info("filter_plugin_init_fn: already loaded "
						   "a plugin with name '%s'. A new Python obj is needed",
						   pName.c_str());

			// Set Python library loaded state
			pythonInitState = h->second->m_init;

			// Set load indicator
			loadModule = true;

			break;
		}
	}

	if (!loadModule)
	{
       		Logger::getLogger()->info("filter_plugin_init_fn: NOT already loaded "
						   "a plugin with name '%s'. A new Python obj is needed",
						   pName.c_str());
		// Plugin name not previously loaded: check current Python module
		// pName is the key
		auto it = pythonModules->find(pName);
		if (it == pythonModules->end())
		{
			Logger::getLogger()->info("plugin_handle: filter_plugin_init(): "
						   "pModule not found for plugin '%s': ",
						   pName.c_str());

			// Set reload indicator
			reloadModule = true;
		}
		else
		{
			Logger::getLogger()->info("plugin_handle: filter_plugin_init(): "
						   "pModule FOUND for plugin '%s': ",
						   pName.c_str());
            
			if (it->second && it->second->m_module)
			{
				// Just use current loaded module: no load or re-load action
				module = it->second;
				Logger::getLogger()->info("plugin_handle: filter_plugin_init(): "
						   "module set to PythonModule object @ address %p",
						   module);

				// Set Python library loaded state
				pythonInitState = it->second->m_init;
			}
			else
			{
				Logger::getLogger()->fatal("plugin_handle: filter_plugin_init(): "
							   "found pModule is NULL for plugin '%s': ",
							   pName.c_str());
				return NULL;
			}
		}
	}

	Logger::getLogger()->info("filter_plugin_init_fn: loadModule=%s, reloadModule=%s", 
                                loadModule?"TRUE":"FALSE", reloadModule?"TRUE":"FALSE");
    
	// Acquire GIL
	PyGILState_STATE state = PyGILState_Ensure();
    
	// Import Python module
	if (loadModule || reloadModule)
	{        
		string fledgePythonDir;

		string fledgeRootDir(getenv("FLEDGE_ROOT"));
		fledgePythonDir = fledgeRootDir + "/python";

		// Set Python path for embedded Python 3.x
		// Get current sys.path - borrowed reference
		PyObject* sysPath = PySys_GetObject((char *)"path");
		PyList_Append(sysPath, PyUnicode_FromString((char *) fledgePythonDir.c_str()));
        
		// Set sys.argv for embedded Python 3.x
		int argc = 2;
		wchar_t* argv[2];
		argv[0] = Py_DecodeLocale("", NULL);
		argv[1] = Py_DecodeLocale(pName.c_str(), NULL);

		// Set script parameters
		PySys_SetArgv(argc, argv);

		Logger::getLogger()->debug("%s_plugin_init_fn, %sloading plugin '%s', ",
					   PLUGIN_TYPE_FILTER,
					   reloadModule ? "re-" : "",
					   pName.c_str());

		// Import Python script
		PyObject *newObj = PyImport_ImportModule(pName.c_str());

		// Check for NULL
		if (newObj)
		{
			PythonModule* newModule;
			if ((newModule = new PythonModule(newObj,
							  pythonInitState,
							  pName,
							  PLUGIN_TYPE_FILTER,
							  NULL)) == NULL)
			{
				// Release lock
				PyGILState_Release(state);

				Logger::getLogger()->fatal("plugin_handle: filter_plugin_init(): "
							   "failed to create Python module "
							   "object, plugin '%s'",
							   pName.c_str());
				return NULL;
			}

			// Set category name
			newModule->setCategoryName(config->getName());

			// Set module
			module = newModule;
		}
		else
		{
			logErrorMessage();

			// Release lock
			PyGILState_Release(state);

			Logger::getLogger()->fatal("plugin_handle: filter_plugin_init(): "
						   "failed to import plugin '%s'",
						   pName.c_str());
			return NULL;
		}
	}
	else
	{
		// Set category name
		module->setCategoryName(config->getName());
	}

	Logger::getLogger()->info("filter_plugin_init_fn for '%s', pModule '%p', "
				   "Python interpreter '%p', config=%s",
				   module->m_name.c_str(),
				   module->m_module,
				   module->m_tState,
				   config->itemsToJSON().c_str());

	Logger::getLogger()->debug("%s:%d: calling set_loglevel_in_python_module(), loglevel=%s", __FUNCTION__, __LINE__, Logger::getLogger()->getMinLevel().c_str());
	set_loglevel_in_python_module(module->m_module, module->m_name + " plugin_init");

	PyObject *config_dict = json_loads(config->itemsToJSON().c_str());
        
	// Call Python method passing an object
	PyObject* ingest_fn = PyCapsule_New((void *)output, NULL, NULL);
	PyObject* ingest_ref = PyCapsule_New((void *)outHandle, NULL, NULL);
	PyObject* pReturn = PyObject_CallMethod(module->m_module,
					"plugin_init",
					"OOO",
					config_dict,
					ingest_ref,
					ingest_fn);

	Py_CLEAR(ingest_ref);
	Py_CLEAR(ingest_fn);

	// Handle returned data
	if (!pReturn)
	{
		Logger::getLogger()->error("Called python script method plugin_init "
                                       ": error while getting result object, plugin '%s'",
                                       pName.c_str());
		logErrorMessage();
	}
	else
	{
		Logger::getLogger()->info("plugin_handle: filter_plugin_init(): "
                                       "got result object '%p', plugin '%s'",
                                       pReturn,
                                       pName.c_str());
	}

	// Add the handle to handles map as key, PythonModule object as value
	std::pair<std::map<PLUGIN_HANDLE, PythonModule*>::iterator, bool> ret;
	if (pythonHandles)
	{
		// Add to handles map the PythonHandles object
		ret = pythonHandles->insert(pair<PLUGIN_HANDLE, PythonModule*>
			((PLUGIN_HANDLE)pReturn, module));

		if (ret.second)
		{
			Logger::getLogger()->debug("plugin_handle: filter_plugin_init_fn(): "
						   "handle %p of python plugin '%s' "
						   "added to pythonHandles map",
						   pReturn,
						   pName.c_str());
		}
		else
		{
			Logger::getLogger()->error("plugin_handle: filter_plugin_init_fn(): "
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
	PyGILState_Release(state);

	return pReturn ? (PLUGIN_HANDLE) pReturn : NULL;
}

/**
 * Constructor for PythonPluginHandle
 *    - Load python interpreter
 *    - Set sys.path and sys.argv
 *
 * @param    pluginName         The plugin name to load
 * @param    pluginPathName     The plugin pathname
 * @return                      PyObject of loaded module
 */
void *PluginInterfaceInit(const char *pluginName, const char * pluginPathName)
{
	bool initPython = true;

	// Set plugin name, also for methods in common-plugin-interfaces/python
	gPluginName = pluginName;

	string fledgePythonDir;
    
	string fledgeRootDir(getenv("FLEDGE_ROOT"));
	fledgePythonDir = fledgeRootDir + "/python";
    
	string filtersRootPath = fledgePythonDir + string(R"(/fledge/plugins/filter/)") + string(pluginName);
	Logger::getLogger()->info("%s:%d:, filtersRootPath=%s", __FUNCTION__, __LINE__, filtersRootPath.c_str());
    
	PythonRuntime::getPythonRuntime();
    
	// Acquire GIL
	PyGILState_STATE state = PyGILState_Ensure();
        
	Logger::getLogger()->info("FilterPlugin PluginInterfaceInit %s:%d: "
				   "fledgePythonDir=%s, plugin '%s'",
				   __FUNCTION__,
				   __LINE__,
				   fledgePythonDir.c_str(),
				   pluginName);

	// Set Python path for embedded Python 3.x
	// Get current sys.path - borrowed reference
	PyObject* sysPath = PySys_GetObject((char *)"path");
	PyList_Append(sysPath, PyUnicode_FromString((char *) filtersRootPath.c_str()));
	PyList_Append(sysPath, PyUnicode_FromString((char *) fledgePythonDir.c_str()));

	// Set sys.argv for embedded Python 3.5
	int argc = 2;
	wchar_t* argv[2];
	argv[0] = Py_DecodeLocale("", NULL);
	argv[1] = Py_DecodeLocale(pluginName, NULL);
	PySys_SetArgv(argc, argv);

	// 2) Import Python script
	PyObject *pModule = PyImport_ImportModule(pluginName);
	Logger::getLogger()->info("%s:%d: pluginName=%s, pModule=%p", __FUNCTION__, __LINE__, pluginName, pModule);

	// Check whether the Python module has been imported
	if (!pModule)
	{
		// Failure
		if (PyErr_Occurred())
		{
			logErrorMessage();
		}
		Logger::getLogger()->fatal("FilterPlugin PluginInterfaceInit: "
					   "cannot import Python module file "
					   "from '%s', plugin '%s'",
					   pluginPathName,
					   pluginName);
	}
	else
	{
		std::pair<std::map<string, PythonModule*>::iterator, bool> ret;
		PythonModule* newModule = NULL;
		if (pythonModules)
		{
			// Add module into pythonModules, pluginName is the key
			if ((newModule = new PythonModule(pModule,
							  initPython,
							  string(pluginName),
							  PLUGIN_TYPE_FILTER,
							  NULL)) == NULL)
			{
				// Release lock
				PyGILState_Release(state);

				Logger::getLogger()->fatal("plugin_handle: filter_plugin_init(): "
							   "failed to create Python module "
							   "object, plugin '%s'",
							   pluginName);

				return NULL;
			}

			ret = pythonModules->insert(pair<string, PythonModule*>
				(string(pluginName), newModule));
			Logger::getLogger()->info("%s:%d: Added pair to pythonModules: <%s, %p>", 
                                        __FUNCTION__, __LINE__, pluginName, newModule);
		}

		// Check result
		if (!pythonModules ||
		    ret.second == false)
		{
			Logger::getLogger()->fatal("%s:%d: python module "
						   "not added to the map "
						   "of loaded plugins, "
						   "pModule=%p, plugin '%s', aborting.",
						   __FUNCTION__,
						   __LINE__,
						   pModule,
						   pluginName);
			// Cleanup
			Py_CLEAR(pModule);
			pModule = NULL;

			delete newModule;
			newModule = NULL;
		}
		else
		{
			Logger::getLogger()->debug("%s:%d: python module "
						   "successfully loaded, "
						   "pModule=%p, plugin '%s'",
						   __FUNCTION__,
						   __LINE__,
						   pModule,
						   pluginName);
		}
	}

	// Release locks
	PyGILState_Release(state);

	// Return new Python module or NULL
	return pModule;
}

/**
 * Returns function pointer that can be invoked to call '_sym' function
 * in python plugin
 *
 * @param    _sym	Symbol name
 * @param    pName	Plugin name
 * @return		function pointer to be invoked
 */
void *PluginInterfaceResolveSymbol(const char *_sym, const string& pName)
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
		Logger::getLogger()->debug("FilterPluginInterface currently "
					   "does not support 'plugin_start', plugin '%s'",
					   pName.c_str());
		return NULL;
	}
	else
	{
		Logger::getLogger()->fatal("FilterPluginInterfaceResolveSymbol can not find symbol '%s' "
					   "in the Filter Python plugin interface library, "
					   "loaded plugin '%s'",
					   _sym,
					   pName.c_str());
		return NULL;
	}
}
}; // End of extern C
