#ifndef _PYTHONREADING_H
#define _PYTHONREADING_H
/*
 * Fledge Python Reading
 *
 * Copyright (c) 2021 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */

#include <reading.h>
#include <Python.h>

/**
 * A wrapper class for a Reading to convert to and from 
 * Python objects.
 */
class PythonReading : public Reading {
	public:
		PythonReading(PyObject *pyReading);
		~PythonReading() {};
		PyObject 		*toPython(bool changeKeys = false, bool bytesString = false);
		static std::string	errorMessage();
		static bool		isArray(PyObject *);
		static bool		doneNumPyImport;

	private:
		PyObject		*convertDatapoint(Datapoint *dp, bool bytesString = false);
		DatapointValue		*getDatapointValue(PyObject *object);
		void 			fixQuoting(std::string& str);
		int			InitNumPy();
};
#endif
