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


PythonRuntime *PythonRuntime::m_instance = 0;

/**
 * Get PythonRuntime singleton instance for the process
 *
 * @return	Singleton PythonRuntime instance
 */
PythonRuntime *PythonRuntime::getPythonRuntime()
{
	if (!m_instance)
	{
		m_instance = new PythonRuntime;
	}
	return m_instance;
}

/**
 * Constructor
 */
PythonRuntime::PythonRuntime()
{
	Py_Initialize();
	PyEval_InitThreads();
	PyThreadState *save = PyEval_SaveThread();	// Release the GIL
}

/**
 * Destructor
 */
PythonRuntime::~PythonRuntime()
{
	PyGILState_STATE gstate = PyGILState_Ensure();
	Py_Finalize();
}

/**
 * Don't allow a copy constructor to be used
 */
PythonRuntime::PythonRuntime(const PythonRuntime& rhs)
{
	throw runtime_error("Illegal attempt to copy a Python runtime");
}

/**
 * Don't allow an assignment to make a copy
 */
PythonRuntime& PythonRuntime::operator=(const PythonRuntime& rhs)
{
	throw runtime_error("Illegal attempt to copy a Python runtime via assignment");
}

/**
 * Execute simple Python script passed as a string
 *
 * @param python	The Python code to run
 */
void PythonRuntime::execute(const string& python)
{
	PyGILState_STATE state = PyGILState_Ensure();
	try {
		PyRun_SimpleString(python.c_str());
	} catch (exception& e) {
		Logger::getLogger()->error("Exception %s executing Python '%s'", e.what(),
				python.c_str());
	}
	PyGILState_Release(state);
}

/**
 * Call a Python function with a set of arguemnts
 *
 * The characters space, tab, colon and comma are ignored in format
 * strings (but not within format units such as s#). This can be used to
 * make long format strings a tad more readable.
 * 
 * s (str or None) [const char *]
 * Convert a null-terminated C string to a Python str object using
 * 'utf-8' encoding. If the C string pointer is NULL, None is used.
 * 
 * s# (str or None) [const char *, Py_ssize_t]
 * Convert a C string and its length to a Python str object using 'utf-8'
 * encoding. If the C string pointer is NULL, the length is ignored and
 * None is returned.
 * 
 * y (bytes) [const char *]
 * This converts a C string to a Python bytes object. If the C string
 * pointer is NULL, None is returned.
 * 
 * y# (bytes) [const char *, Py_ssize_t]
 * This converts a C string and its lengths to a Python object. If the
 * C string pointer is NULL, None is returned.
 * 
 * z (str or None) [const char *]
 * Same as s.
 * 
 * z# (str or None) [const char *, Py_ssize_t]
 * Same as s#.
 * 
 * u (str) [const wchar_t *]
 * Convert a null-terminated wchar_t buffer of Unicode (UTF-16 or UCS-4)
 * data to a Python Unicode object. If the Unicode buffer pointer is NULL,
 * None is returned.
 * 
 * u# (str) [const wchar_t *, Py_ssize_t]
 * Convert a Unicode (UTF-16 or UCS-4) data buffer and its length to
 * a Python Unicode object. If the Unicode buffer pointer is NULL, the
 * length is ignored and None is returned.
 * 
 * U (str or None) [const char *]
 * Same as s.
 * 
 * U# (str or None) [const char *, Py_ssize_t]
 * Same as s#.
 * 
 * i (int) [int]
 * Convert a plain C int to a Python integer object.
 * 
 * b (int) [char]
 * Convert a plain C char to a Python integer object.
 * 
 * h (int) [short int]
 * Convert a plain C short int to a Python integer object.
 * 
 * l (int) [long int]
 * Convert a C long int to a Python integer object.
 * 
 * B (int) [unsigned char]
 * Convert a C unsigned char to a Python integer object.
 * 
 * H (int) [unsigned short int]
 * Convert a C unsigned short int to a Python integer object.
 * 
 * I (int) [unsigned int]
 * Convert a C unsigned int to a Python integer object.
 * 
 * k (int) [unsigned long]
 * Convert a C unsigned long to a Python integer object.
 * 
 * L (int) [long long]
 * Convert a C long long to a Python integer object.
 * 
 * K (int) [unsigned long long]
 * Convert a C unsigned long long to a Python integer object.
 * 
 * n (int) [Py_ssize_t]
 * Convert a C Py_ssize_t to a Python integer.
 * 
 * c (bytes of length 1) [char]
 * Convert a C int representing a byte to a Python bytes object of length 1.
 * 
 * C (str of length 1) [int]
 * Convert a C int representing a character to Python str object of length 1.
 * 
 * d (float) [double]
 * Convert a C double to a Python floating point number.
 * 
 * f (float) [float]
 * Convert a C float to a Python floating point number.
 * 
 * D (complex) [Py_complex *]
 * Convert a C Py_complex structure to a Python complex number.
 * 
 * O (object) [PyObject *]
 * Pass a Python object untouched (except for its reference count, which
 * is incremented by one). If the object passed in is a NULL pointer, it
 * is assumed that this was caused because the call producing the argument
 * found an error and set an exception. Therefore, Py_BuildValue() will
 * return NULL but won’t raise an exception. If no exception has been
 * raised yet, SystemError is set.
 * 
 * S (object) [PyObject *]
 * Same as O.
 * 
 * N (object) [PyObject *]
/bin/bash: ft: command not found
 * 
 * O& (object) [converter, anything]
 * Convert anything to a Python object through a converter function. The
 * function is called with anything (which should be compatible with void*)
 * as its argument and should return a “new” Python object, or NULL
 * if an error occurred.
 * 
 * (items) (tuple) [matching-items]
 * Convert a sequence of C values to a Python tuple with the same number of items.
 * 
 * [items] (list) [matching-items]
 * Convert a sequence of C values to a Python list with the same number of items.
 * 
 * {items} (dict) [matching-items]
 * Convert a sequence of C values to a Python dictionary. Each pair of
 * consecutive C values adds one item to the dictionary, serving as key
 * and value, respectively.
 * 
 *
 * @param fcn	The name of the function to call
 * @param fmt	The buildValue style format string for the arguments
 * @return PyObject* The function result
 */
PyObject *PythonRuntime::call(const string& fcn, const string& fmt, ...)
{
PyObject *rval = NULL;
va_list ap;
PyObject *mod, *method;

	PyGILState_STATE state = PyGILState_Ensure();
	if ((mod = PyImport_ImportModule("__main__")) != NULL)
	{
		if ((method = PyObject_GetAttrString(mod, fcn.c_str())) != NULL)
		{
			va_start(ap, fmt);
			PyObject *args = Py_VaBuildValue(fmt.c_str(), ap);
			va_end(ap);
			rval = PyObject_Call(method, args, NULL);
			if (rval == NULL)
			{
				if (PyErr_Occurred())
				{
					logException(fcn);
					PyErr_Print();
				}
			}
			Py_CLEAR(method);
		}
		else
		{
			Logger::getLogger()->fatal("Method '%s' not found", fcn.c_str());
		}
		// Remove references
		Py_CLEAR(mod);
	}
	else
	{
		Logger::getLogger()->fatal("Failed to import module");
	}

	// Reset error
	PyErr_Clear();

	PyGILState_Release(state);

	return rval;
}

/**
 * Call a Python function within a specified module.
 *
 * The using the same formattign rules as the call method above
 *
 * @param module	The module in which the function was imported
 * @param fcn	The name of the function to call
 * @param fmt	The buildValue style format string for the arguments
 * @return PyObject* The function result
 */
PyObject *PythonRuntime::call(PyObject *module, const string& fcn, const string& fmt, ...)
{
PyObject *rval;
va_list ap;
PyObject *method;

	PyGILState_STATE state = PyGILState_Ensure();
	if ((method = PyObject_GetAttrString(module, fcn.c_str())) != NULL)
	{
		va_start(ap, fmt);
		PyObject *args = Py_VaBuildValue(fmt.c_str(), ap);
		va_end(ap);
		rval = PyObject_Call(method, args, NULL);
		if (rval == NULL)
		{
			if (PyErr_Occurred())
			{
				logException(fcn);
				PyErr_Print();
			}
		}
		Py_CLEAR(method);
	}
	else
	{
		Logger::getLogger()->fatal("Method '%s' not found", fcn.c_str());
	}

	// Reset error
	PyErr_Clear();

	PyGILState_Release(state);

	return rval;
}

/**
 * Import a Python module
 *
 * @param name	The name of the module to import
 * @return PyObject* The Python module
 */
PyObject *PythonRuntime::importModule(const string& name)
{
	PyGILState_STATE state = PyGILState_Ensure();
	PyObject *module = PyImport_ImportModule(name.c_str());
	if (!module)
	{
		Logger::getLogger()->error("Failed to import Python module %s", name.c_str());
		if (PyErr_Occurred())
		{
			logException(name);
		}
	}
	PyGILState_Release(state);
	return module;
}

/**
 * Shutdown an instance of a Python runtime if one
 * has been started
 */
void PythonRuntime::shutdown()
{
	if (!m_instance)
	{
		return;
	}
	delete m_instance;
	m_instance = NULL;
}
