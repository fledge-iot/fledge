/*
 * Fledge python module for filter plugin ingest callback
 *
 * Copyright (c) 2019 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Massimiliano Pinto
 */

#include <reading.h>
#include <reading_set.h>
#include <logger.h>
#include <Python.h>
#include <vector>
#include <pythonreadingset.h>

extern "C" {

typedef void (*INGEST_CB_DATA)(void *, PythonReadingSet *);

static void filter_plugin_async_ingest_fn(PyObject *ingest_callback,
				    PyObject *ingest_obj_ref_data,
				    PyObject *readingsObj);

static PyObject *IngestError;

/**
 * Implementation of data ingest into filters chain
 *
 * @param    self       The python module object
 * @param    args       Input arguments
 * @return              PyObject of None type
 */
static PyObject *filter_ingest_callback(PyObject *self, PyObject *args)
{
	PyObject *readingList;
	PyObject *callback;
	PyObject *ingestData;

	if (!PyArg_ParseTuple(args,
			      "OOO",
			      &callback,
			      &ingestData,
			      &readingList))
	{
		Logger::getLogger()->error("Cannot parse input arguments "
					   "of filter_ingest_callback C API module");
		return NULL;
	}

	// Invoke callback routine
	filter_plugin_async_ingest_fn(callback,
				ingestData,
				readingList);

	Py_INCREF(Py_None);
	return Py_None;
}

static PyMethodDef FilterIngestMethods[] = {
	{
		"filter_ingest_callback",
		filter_ingest_callback,
		METH_VARARGS,
		"Invoke filter ingest callback"
	},
	{NULL, NULL, 0, NULL}    /* Sentinel */
};

static struct PyModuleDef filterIngestmodule = {
	PyModuleDef_HEAD_INIT,
	"filter_ingest",   /* name of module */
	NULL, 		/* module documentation, may be NULL */
	-1,       	/* size of per-interpreter state of the module,
	             or -1 if the module keeps state in global variables. */
	FilterIngestMethods
};

/**
 * Init the C API Python module
 */
PyMODINIT_FUNC
PyInit_filter_ingest(void)
{	
	PyObject *m;

	m = PyModule_Create(&filterIngestmodule);
	if (m == NULL)
	{
		Logger::getLogger()->fatal("Cannot initialise filter_ingest C API module");
		return NULL;
	}

	IngestError = PyErr_NewException("ingest.error", NULL, NULL);
	Py_INCREF(IngestError);
	PyModule_AddObject(m, "error", IngestError);

	return m;
}

/**
 * Ingest data into filters chain
 *
 * @param    ingest_callback            The callback routine
 * @param    ingest_obj_ref_data        Object parameter for callback routine
 * @param    readingsObj                Readongs data as PyObject
 */
void filter_plugin_async_ingest_fn(PyObject *ingest_callback,
			     PyObject *ingest_obj_ref_data,
			     PyObject *readingsObj)
{
	if (ingest_callback == NULL ||
	    ingest_obj_ref_data == NULL ||
	    readingsObj == NULL)
	{
		Logger::getLogger()->error("PyC interface error: "
					   "%s: "
					   "filter_ingest_callback=%p, "
					   "ingest_obj_ref_data=%p, "
					   "readingsObj=%p",
					   __FUNCTION__,
					   ingest_callback,
					   ingest_obj_ref_data,
					   readingsObj);
		return;
	}
	
	PythonReadingSet *pyReadingSet = NULL;
    
	// Check we have a list of readings
	if (PyList_Check(readingsObj))
	{
		try
		{
			// Get vector of Readings from Python object
			pyReadingSet = new PythonReadingSet(readingsObj);
		}
		catch (std::exception e)
		{
			Logger::getLogger()->warn("Unable to create a PythonReadingSet, error: %s", e.what());
			pyReadingSet = NULL;
		}
        
		Logger::getLogger()->debug("%s:%d, pyReadingSet=%p, pyReadingSet readings count=%d", 
                                    __FUNCTION__, __LINE__, pyReadingSet, pyReadingSet?pyReadingSet->getCount():0);
	}
	else
	{
		Logger::getLogger()->error("Filter did not return a Python List "
					   "but object type %s",
					   Py_TYPE(readingsObj)->tp_name);
	}

	// From: https://docs.python.org/3/c-api/arg.html
	// Note that any Python object references which are provided to the caller are borrowed references; 
	// do not decrement their reference count!

	/*if(readingsObj)
		Py_CLEAR(readingsObj);*/

	if (pyReadingSet)
	{
		// Get callback pointer
		INGEST_CB_DATA cb = (INGEST_CB_DATA) PyCapsule_GetPointer(ingest_callback, NULL);
        
		// Get ingest object parameter
		void *data = PyCapsule_GetPointer(ingest_obj_ref_data, NULL);

		Logger::getLogger()->debug("%s:%d: cb function at address %p", __FUNCTION__, __LINE__, *cb);
		// Invoke callback method for ReadingSet filter ingestion
		(*cb)(data, pyReadingSet);
	}
	else
	{
		Logger::getLogger()->error("PyC interface: plugin_ingest_fn: "
					   "Got invalid ReadingSet while converting from PyObject");
	}
}
}; // end of extern "C" block
