#ifndef _PYTHONREADING_H
#define _PYTHONREADING_H

#include <reading.h>
#include <Python.h>
#define	PY_ARRAY_UNIQUE_SYMBOL	PyArray_API_FLEDGE
#include <numpy/npy_common.h>
#define NPY_NO_DEPRECATED_API NPY_1_7_API_VERSION
#include <numpy/ndarraytypes.h>
#include <numpy/ndarrayobject.h>

#undef NUMPY_IMPORT_ARRAY_RETVAL
#define NUMPY_IMPORT_ARRAY_RETVAL	0

/**
 * A wrapper class for a Reading to convert too and from 
 * Python objects.
 */
class PythonReading : public Reading {
	public:
		PythonReading(PyObject *pyReading);
		PyObject 		*toPython();
		static std::string	errorMessage();
		static bool		doneNumPyImport;
	private:
		PyObject		*convertDatapoint(Datapoint *dp);
		DatapointValue		*getDatapointValue(PyObject *object);
		void 			fixQuoting(std::string& str);
		int			InitNumPy()
					{
						if (!PythonReading::doneNumPyImport)
						{
							PythonReading::doneNumPyImport = true;
							import_array();
						}
					};
};
#endif
