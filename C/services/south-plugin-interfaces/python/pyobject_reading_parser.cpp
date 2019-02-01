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

extern "C" {

static void logErrorMessage();

/**
 * Creating Reading object from Python object
 *
 * @param element	Python 3.5 Object (dict)
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

	// Get 'asset_code' value: borrowed reference.
	PyObject* assetCode = PyDict_GetItemString(element,
						   "asset");
	// Get 'reading' value: borrowed reference.
	PyObject* reading = PyDict_GetItemString(element,
						 "readings");
	// Keys not found or reading is not a dict
	if (!assetCode ||
		!reading ||
		!PyDict_Check(reading))
	{
		// Failure
		if (PyErr_Occurred())
		{
			logErrorMessage();
		}
		return NULL;
	}

	// Fetch all Datapoins in 'reading' dict			
	PyObject *dKey, *dValue;  // borrowed references set by PyDict_Next()
	Py_ssize_t dPos = 0;
	Reading* newReading = NULL;

	// Fetch all Datapoints in 'reading' dict
	// dKey and dValue are borrowed references
	while (PyDict_Next(reading, &dPos, &dKey, &dValue))
	{
		DatapointValue* dataPoint;
		if (PyLong_Check(dValue) || PyLong_Check(dValue))
		{
			dataPoint = new DatapointValue((long)PyLong_AsUnsignedLongMask(dValue));
		}
		else if (PyFloat_Check(dValue))
		{
			dataPoint = new DatapointValue(PyFloat_AS_DOUBLE(dValue));
		}
		else if (PyBytes_Check(dValue))
		{
			dataPoint = new DatapointValue(std::string(PyUnicode_AsUTF8(dValue)));
		}
		else if (PyUnicode_Check(dValue))
		{
			dataPoint = new DatapointValue(std::string(PyUnicode_AsUTF8(dValue)));
		}
		else
		{
			Logger::getLogger()->info("Unable to parse dValue in readings dict: dKey=%s, Py_TYPE(dValue)=%s", 
									std::string(PyUnicode_AsUTF8(dKey)).c_str(), (Py_TYPE(dValue))->tp_name);
			//delete dataPoint;
			return NULL;
		}

		// Add / Update the new Reading data			
		if (newReading == NULL)
		{
			newReading = new Reading(std::string(PyUnicode_AsUTF8(assetCode)),
						 new Datapoint(std::string(PyUnicode_AsUTF8(dKey)),
								   *dataPoint));
		}
		else
		{
			newReading->addDatapoint(new Datapoint(std::string(PyUnicode_AsUTF8(dKey)),
								   *dataPoint));
		}

		/**
		 * Set id, uuid, ts and user_ts of the original data
		 */

		// Get 'id' value: borrowed reference.
		PyObject* id = PyDict_GetItemString(element, "id");
		if (id && PyLong_Check(id))
		{
			// Set id
			newReading->setId(PyLong_AsUnsignedLong(id));
		}

		// Get 'ts' value: borrowed reference.
		PyObject* ts = PyDict_GetItemString(element, "ts");
		if (ts)
		{
			// Convert a timestamp of the from 2019-01-07 19:06:35.366100+01:00
			char *ts_str = PyUnicode_AsUTF8(ts);
                        newReading->setTimestamp(ts_str);
		}

		// Get 'user_ts' value: borrowed reference.
		PyObject* uts = PyDict_GetItemString(element, "timestamp");
		if (uts)
		{
			// Convert a timestamp of the from 2019-01-07 19:06:35.366100+01:00
			char *ts_str = PyUnicode_AsUTF8(uts);
                        newReading->setUserTimestamp(ts_str);
                }
		
		// Get 'uuid' value: borrowed reference.
		PyObject* uuid = PyDict_GetItemString(element, "key");
		if (uuid && PyUnicode_Check(uuid))
		{
			// Set uuid
			newReading->setUuid(std::string(PyUnicode_AsUTF8(uuid)));
		}

		// Remove temp objects
		delete dataPoint;
	}
	return newReading;
}

/**
 * Creating vector of Reading objects from Python object
 *
 * @param element	Python 3.5 Object (dict)
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
			Reading* newReading = Py2C_parseReadingObject(element);
			if (newReading)
			{
				// Add the new reading to result vector
				newReadings->push_back(newReading);
			}
			//else
				//Logger::getLogger()->info("Py2C_getReadings: Reading[%d] is NULL", i);
		}
	}
	else // just a single reading, no list
	{
		Reading* newReading = Py2C_parseReadingObject(polledData);
		if (newReading)
			newReadings->push_back(newReading);
	}
	
	return newReadings;
	
}

/**
 * Function to log error message encountered while interfacing with
 * Python runtime
 */
static void logErrorMessage()
{
	PRINT_FUNC;
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
};
