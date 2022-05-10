/*
 * Fledge Python runtime
 *
 * Copyright (c) 2021 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */

#include <logger.h>
#include <pyruntime.h>
#include <Python.h>
#include <stdexcept>
#include <stdarg.h>

using namespace std;

/**
 * Log an exception from a Python rotuine including the stack track formatted into the
 * error log.
 *
 * @param name	The name to attached to the exception trace.
 */
void PythonRuntime::logException(const string& name)
{
	PyObject* type;
	PyObject* value;
	PyObject* traceback;


	PyErr_Fetch(&type, &value, &traceback);
	PyErr_NormalizeException(&type, &value, &traceback);

	PyObject* str_exc_value = PyObject_Repr(value);
	PyObject* pyExcValueStr = PyUnicode_AsEncodedString(str_exc_value, "utf-8", "Error ~");
	const char* pErrorMessage = value ?
				    PyBytes_AsString(pyExcValueStr) :
				    "no error description.";
	Logger::getLogger()->fatal("Python Runtime: %s: Error '%s'", name.c_str(), pErrorMessage);
	
	// Check for numpy/pandas import errors
	const char *err1 = "implement_array_function method already has a docstring";
	const char *err2 = "cannot import name 'check_array_indexer' from 'pandas.core.indexers'";

	
	std::string fcn = "";
	fcn += "def get_pretty_traceback(exc_type, exc_value, exc_tb):\n";
	fcn += "    import sys, traceback\n";
	fcn += "    lines = []\n"; 
	fcn += "    lines = traceback.format_exception(exc_type, exc_value, exc_tb)\n";
	fcn += "    return lines\n";

	PyRun_SimpleString(fcn.c_str());
	PyObject* mod = PyImport_ImportModule("__main__");
	if (mod != NULL)
	{
		PyObject* method = PyObject_GetAttrString(mod, "get_pretty_traceback");
		if (method != NULL)
		{
			PyObject* outList = PyObject_CallObject(method, Py_BuildValue("OOO", type, value, traceback));
			if (outList != NULL)
			{
				if (PyList_Check(outList))
				{
					Py_ssize_t listSize = PyList_Size(outList);
					for (Py_ssize_t i = 0; i < listSize; i++)
					{
						PyObject *tmp = PyUnicode_AsASCIIString(PyList_GetItem(outList, i));
						Logger::getLogger()->fatal("%s",
								PyBytes_AsString(tmp));
					}
				}
				else
					Logger::getLogger()->error("Expected a list");
			}
		}
		Py_CLEAR(method);
	}

	// Reset error
	PyErr_Clear();

	// Remove references
	Py_CLEAR(type);
	Py_CLEAR(value);
	Py_CLEAR(traceback);
	Py_CLEAR(str_exc_value);
	Py_CLEAR(pyExcValueStr);
	Py_CLEAR(mod);
}
