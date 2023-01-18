/*
 * Fledge python module for async plugin ingest callback
 *
 * Copyright (c) 2019 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Amandeep Singh Arora
 */

#include <reading.h>
#include <logger.h>
#include <Python.h>
#include <vector>
#include <pythonreadingset.h>

extern "C" {

typedef void (*INGEST_CB2)(void *, PythonReadingSet *);

void plugin_ingest_fn(PyObject *ingest_callback, PyObject *ingest_obj_ref_data, PyObject *readingsObj);

static PyObject *IngestError;

static PyObject *
ingest_callback(PyObject *self, PyObject *args)
{
	PyObject *readingList;
	PyObject *callback;
	PyObject *ingestData;

	if (!PyArg_ParseTuple(args, "OOO", &callback, &ingestData, &readingList))
		return NULL;

	plugin_ingest_fn(callback, ingestData, readingList);

	Py_INCREF(Py_None);
	return Py_None;
}

static PyMethodDef IngestMethods[] = {
	{"ingest_callback",  ingest_callback, METH_VARARGS, "Invoke ingest callback"},
	{NULL, NULL, 0, NULL}        /* Sentinel */
};

static struct PyModuleDef ingestmodule = {
	PyModuleDef_HEAD_INIT,
	"async_ingest",   /* name of module */
	NULL, 		/* module documentation, may be NULL */
	-1,       	/* size of per-interpreter state of the module,
	             or -1 if the module keeps state in global variables. */
	IngestMethods
};

PyMODINIT_FUNC
PyInit_async_ingest(void)
{	
	PyObject *m;

	m = PyModule_Create(&ingestmodule);
	if (m == NULL)
		return NULL;

	Logger::getLogger()->debug("PyModule_Create() succeeded");

	IngestError = PyErr_NewException("ingest.error", NULL, NULL);
	Py_INCREF(IngestError);
	PyModule_AddObject(m, "error", IngestError);

	Logger::getLogger()->debug("PyInit_ingest() returning");
	return m;
}

void plugin_ingest_fn(PyObject *ingest_callback, PyObject *ingest_obj_ref_data, PyObject *readingsObj)
{
	if (ingest_callback == NULL || ingest_obj_ref_data == NULL || readingsObj == NULL)
	{
		Logger::getLogger()->error("Py2C interface: plugin_ingest_fn: ingest_callback=%p, ingest_obj_ref_data=%p, readingsObj=%p",
						ingest_callback, ingest_obj_ref_data, readingsObj);
		return;
	}

    PythonReadingSet *pyReadingSet = NULL;

    try
    {
        pyReadingSet = new PythonReadingSet(readingsObj);
    }
    catch (std::exception e)
    {
		Logger::getLogger()->warn("PythonReadingSet c'tor failed, error: %s", e.what());
        pyReadingSet = NULL;
	}
    
    // Py_XDECREF(readingsObj);

	if(pyReadingSet)
	{
		INGEST_CB2 cb = (INGEST_CB2) PyCapsule_GetPointer(ingest_callback, NULL);
		void *data = PyCapsule_GetPointer(ingest_obj_ref_data, NULL);
		(*cb)(data, pyReadingSet);
	}
	else
		Logger::getLogger()->error("Py2C interface: plugin_ingest_fn: PythonReadingSet c'tor returned NULL");
}
}; // end of extern "C" block
