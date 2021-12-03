/*
 * Helper functions to parse python object to 
 * (vector of) Reading object(s)
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
#include <pythonreading.h>
#include <stdexcept>
#include <exception>

extern "C" {

static void logErrorMessage();

/**
 * Creating Reading object from Python object
 *
 * @param element	Python Object (dict)
 * @return		Pointer to a new Reading object
 *				or NULL in case of error
 */
Reading* Py2C_parseReadingObject(PyObject *element)
{
	// Get list item: borrowed reference.
	if (!element)
	{
		// Failure
		if (PyErr_Occurred())
		{
			logErrorMessage();
		}
		return NULL;
	}
	if (!PyDict_Check(element))
	{
		// Failure
		if (PyErr_Occurred())
		{
			logErrorMessage();
		}
		return NULL;
	}
	
	return new PythonReading(element);
}

/**
 * Creating vector of Reading objects from Python object
 *
 * @param polledData	Python Object (dict)
 * @return		Pointer to a vector of Reading objects
 *				or NULL in case of error
 */
std::vector<Reading *>* Py2C_getReadings(PyObject *polledData)
{
	std::vector<Reading *>* newReadings = new std::vector<Reading *>();

	if(PyList_Check(polledData)) // got a list of readings
	{
		// Iterate reading objects in the list
		for (int i = 0; i < PyList_Size(polledData); i++)
		{
			// Get list item: borrowed reference.
			PyObject* element = PyList_GetItem(polledData, i);
			if (!element)
			{
				// Failure
				if (PyErr_Occurred())
				{
					logErrorMessage();
				}
				delete newReadings;

				return NULL;
			}
			Reading* newReading = new PythonReading(element);
			if (newReading)
			{
				// Add the new reading to result vector
				newReadings->push_back(newReading);
			}
		}
	}
	else // a dict, possibly containing multiple readings
	{
		if (polledData && PyDict_Check(polledData))
		{
			// Get 'reading' value: borrowed reference.
			// Look inside for "reading" field to determine the helper function to parse readings
			PyObject* reading = PyDict_GetItemString(polledData,
								 "readings");
			if (reading && PyList_Check(reading))
			{
				delete newReadings;
//				newReadings = Py2C_parseReadingListObject(polledData);
				throw std::runtime_error("Badly formatted list of readings from Python");
			}
			else // just a single reading, no list
			{
				Reading* newReading = new PythonReading(polledData);
				if (newReading)
					newReadings->push_back(newReading);
			}
		}
	}
	return newReadings;
}

/**
 * Function to log error message encountered while interfacing with
 * Python runtime
 */
static void logErrorMessage()
{
	//Get error message
	PyObject *pType, *pValue, *pTraceback;
	PyErr_Fetch(&pType, &pValue, &pTraceback);

	// NOTE from :
	// https://docs.python.org/2/c-api/exceptions.html
	//
	// The value and traceback object may be NULL
	// even when the type object is not.	
	const char* pErrorMessage = pValue ?
					PyBytes_AsString(pValue) :
					"no error description.";

	Logger::getLogger()->fatal("logErrorMessage: Error '%s' ",
					pErrorMessage ?
					pErrorMessage :
					"no description");

	// Reset error
	PyErr_Clear();

	// Remove references
	Py_CLEAR(pType);
	Py_CLEAR(pValue);
	Py_CLEAR(pTraceback);
}

/**
 * Create a list of dict Python object (PyList) from
 * a vector of Reading pointers
 *
 * @param    readings	The input readings vector
 * @return		PyList object on success or NULL on errors
 */
PyObject* createReadingsList(const std::vector<Reading *>& readings, bool changeDictKeys)
{
	// TODO add checks to all PyList_XYZ methods
	PyObject* readingsList = PyList_New(0);

	// Iterate the input readings
	for (std::vector<Reading *>::const_iterator elem = readings.begin();
                                                      elem != readings.end();
                                                      ++elem)
	{
		// Create an object (dict) with 'asset_code' and 'readings' key
		PyObject* readingObject = ((PythonReading *)(*elem))->toPython(changeDictKeys);

		// Add new object to the list
		PyList_Append(readingsList, readingObject);

		// Remove temp objects
		Py_CLEAR(readingObject);
	}

	// Return pointer of new allocated list
	return readingsList;
}
}; // End of extern C
