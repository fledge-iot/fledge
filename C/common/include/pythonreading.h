#ifndef _PYTHONREADING_H
#define _PYTHONREADING_H

#include <reading.h>
#include <Python.h>

/**
 * A wrapper class for a Reading to convert too and from 
 * Python objects.
 */
class PythonReading : public Reading {
	public:
		PythonReading(PyObject *pyReading);
		PyObject 		*toPython();
		static std::string	errorMessage();
	private:
		void 			fixQuoting(std::string& str);
};
#endif
