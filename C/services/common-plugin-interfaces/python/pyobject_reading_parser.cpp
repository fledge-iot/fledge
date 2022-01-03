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
 * Set id, uuid, ts and user_ts in the reading object
 *
 * @param newReading	Reading object to update
 * @param readingList	PyObject containing this reading object
 * @param fillIfMissing	If True, only fill ID/TS fields if not set already
 */
void setReadingAttr(Reading* newReading, PyObject *readingList, bool fillIfMissing)
{
	if (!newReading)
		return;
	
	// Get 'id' value: borrowed reference.
	PyObject* id = PyDict_GetItemString(readingList, "id");
    bool fill = (!fillIfMissing || (fillIfMissing && newReading->getId()==0));
	if (fill && id && PyLong_Check(id))
	{
		// Set id
		newReading->setId(PyLong_AsUnsignedLong(id));
	}

	// Get 'ts' value: borrowed reference.
	PyObject* ts = PyDict_GetItemString(readingList, "ts");
    fill = (!fillIfMissing || (fillIfMissing && newReading->getTimestamp()==0));
	if (fill && ts)
	{
		// Convert a timestamp of the from '2019-01-07 19:06:35.366100+01:00'
		const char *ts_str = PyUnicode_AsUTF8(ts);
		newReading->setTimestamp(ts_str);
	}

	// Get 'user_ts' value: borrowed reference.
	PyObject* uts = PyDict_GetItemString(readingList, "timestamp");
    fill = (!fillIfMissing || (fillIfMissing && newReading->getUserTimestamp()==0));
	if (fill && uts)
	{
		// Convert a timestamp of the from '2019-01-07 19:06:35.366100+01:00'
		const char *ts_str = PyUnicode_AsUTF8(uts);
		newReading->setUserTimestamp(ts_str);
	}
	
	// Get 'ts' value: borrowed reference.
	PyObject* userts = PyDict_GetItemString(readingList, "user_ts");
    fill = (!fillIfMissing || (fillIfMissing && newReading->getUserTimestamp()==0));
	if (fill && userts)
	{
		// Convert a timestamp of the from '2019-01-07 19:06:35.366100+01:00'
		const char *ts_str = PyUnicode_AsUTF8(userts);
		newReading->setUserTimestamp(ts_str);
	}

    // if User TS is still not filled, copy TS into it
    fill = (!fillIfMissing || (fillIfMissing && newReading->getUserTimestamp()==0));
    //Logger::getLogger()->debug("fill=%s, newReading->getUserTimestamp()=%d, newReading->getTimestamp()=%d", fill?"True":"False", newReading->getUserTimestamp(), newReading->getTimestamp());
    if (fill)
    {
        newReading->setUserTimestamp(newReading->getTimestamp());
        //Logger::getLogger()->debug("Copied TS into user TS: newReading->getUserTimestamp()=%d", newReading->getUserTimestamp());
    }
}


#if 0
/**
 * Creating vector of Reading objects from Python object
 *
 * @param polledData	Python Object (dict)
 * @return		Pointer to a vector of Reading objects
 *				or NULL in case of error
 */
std::vector<Reading *>* Py2C_getReadings(PyObject *polledData)
{
    PyObject* objectsRepresentation = PyObject_Repr(polledData);
    const char* s = PyUnicode_AsUTF8(objectsRepresentation);
    Logger::getLogger()->info("Py2C_getReadings(): polledData=%s", s);
    
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
                setReadingAttr(newReading, polledData, true);
                //Logger::getLogger()->info("Py2C_getReadings:L%d: reading=%s", __LINE__, newReading->toJSON().c_str());
                
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
				{
                    setReadingAttr(newReading, polledData, true);
                    //Logger::getLogger()->info("Py2C_getReadings:L%d: reading=%s", __LINE__, newReading->toJSON().c_str());

                    // Add the new reading to result vector
					newReadings->push_back(newReading);
				}
			}
		}
	}
	return newReadings;
}
#endif

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

    PyObject* objectsRepresentation = PyObject_Repr(readingsList);
    const char* s = PyUnicode_AsUTF8(objectsRepresentation);
    Logger::getLogger()->info("C2Py: createReadingsList():L%d: readingsList=%s", __LINE__, s);
    Py_CLEAR(objectsRepresentation);
	// Return pointer of new allocated list
	return readingsList;
}
}; // End of extern C
