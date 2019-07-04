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
DatapointValue* Py2C_createDictDPV(PyObject *data);
DatapointValue* Py2C_createListDPV(PyObject *data);


/**
 * Creating DatapointValue object from Python object
 *
 * @param dValue	Python Object
 * @return		Pointer to a new DatapointValue object
 *				or NULL in case of error
 */
DatapointValue *Py2C_createBasicDPV(PyObject *dValue)
{
	if (!dValue)
	{
		Logger::getLogger()->info("dValue is NULL");
		return NULL;
	}
	DatapointValue* dpv;
	if (PyLong_Check(dValue))
	{
		dpv = new DatapointValue((long)PyLong_AsUnsignedLongMask(dValue));
	}
	else if (PyFloat_Check(dValue))
	{
		dpv = new DatapointValue(PyFloat_AS_DOUBLE(dValue));
	}
	else if (PyBytes_Check(dValue) || PyUnicode_Check(dValue))
	{
		dpv = new DatapointValue(std::string(PyUnicode_AsUTF8(dValue)));
	}
	else
	{
		Logger::getLogger()->info("Unable to parse dValue: Py_TYPE(dValue)=%s", (Py_TYPE(dValue))->tp_name);
		dpv = NULL;
	}
	return dpv;
}

/**
 * Creating DatapointValue object from Python object
 *
 * @param data	Python Object (dict)
 * @return		Pointer to a new DatapointValue object
 *				or NULL in case of error
 */
DatapointValue* Py2C_createDictDPV(PyObject *data)
{
	if(!data || !PyDict_Check(data)) // got a dict of DPs
	{
		Logger::getLogger()->info("data is NULL or not a PyDict");
		return NULL;
	}
	
	// Fetch all Datapoints in the dict			
	PyObject *dKey, *dValue;  // borrowed references set by PyDict_Next()
	Py_ssize_t dPos = 0;
	Reading* newReading = NULL;
	
	std::vector<Datapoint*> *dpVec = new std::vector<Datapoint*>();
	
	// Fetch all Datapoints in 'reading' dict
	// dKey and dValue are borrowed references
	while (PyDict_Next(data, &dPos, &dKey, &dValue))
	{
		DatapointValue* dpv;
		if (PyLong_Check(dValue) || PyFloat_Check(dValue) || PyBytes_Check(dValue) || PyUnicode_Check(dValue))
		{
			dpv = Py2C_createBasicDPV(dValue);
		}
		else if (PyList_Check(dValue))
		{
			dpv = Py2C_createListDPV(dValue);
		}
		else if (PyDict_Check(dValue))
		{
			dpv = Py2C_createDictDPV(dValue);
		}
		else
		{
			Logger::getLogger()->info("Unable to parse dValue in 'data' dict: dKey=%s, Py_TYPE(dValue)=%s", std::string(PyUnicode_AsUTF8(dKey)).c_str(), (Py_TYPE(dValue))->tp_name);
			dpv = NULL;
		}
		if (dpv)
		{
			dpVec->emplace_back(new Datapoint(std::string(PyUnicode_AsUTF8(dKey)), *dpv));
			delete dpv;
		}
	}
	
	if (dpVec->size() > 0)
	{
		DatapointValue *dpv = new DatapointValue(dpVec, true);
		return dpv;
	}
	else
	{
		return NULL;
	}
}

/**
 * Creating DatapointValue object from Python object
 *
 * @param data	Python Object (list)
 * @return		Pointer to a new DatapointValue object
 *				or NULL in case of error
 */
DatapointValue* Py2C_createListDPV(PyObject *data)
{
	if(!data || !PyList_Check(data)) // got a list of DPs
	{
		Logger::getLogger()->info("data is NULL or not a PyList");
		return NULL;
	}
	
	std::vector<Datapoint*>* dpVec = new std::vector<Datapoint *>();
	// Iterate DPV objects in the list
	for (int i = 0; i < PyList_Size(data); i++)
	{
		DatapointValue* dpv = NULL;
		// Get list item: borrowed reference.
		PyObject* element = PyList_GetItem(data, i);
		if (!element)
		{
			// Failure
			if (PyErr_Occurred())
			{
				logErrorMessage();
			}
			delete dpVec;

			return NULL;
		}
		else if (PyDict_Check(element))
		{
			dpv = Py2C_createDictDPV(element);
		}
		else if (PyList_Check(element))
		{
			dpv = Py2C_createListDPV(element);
		}
		else if (PyLong_Check(element) || PyFloat_Check(element) || PyBytes_Check(element) || PyUnicode_Check(element))
		{
			dpv = Py2C_createBasicDPV(element);
		}
		if (dpv)
		{
			dpVec->emplace_back(new Datapoint(std::string("unnamed_list_elem#") + std::to_string(i), *dpv));
			delete dpv;
		}
	}
	
	if (dpVec->size() > 0)
	{
		DatapointValue *dpv = new DatapointValue(dpVec, false);
		return dpv;
	}
	else
	{
		return NULL;
	}
}

/**
 * Set id, uuid, ts and user_ts in the reading object
 *
 * @param newReading	Reading object to update
 * @param element		PyObject containing this reading object
 */
void setReadingAttr(Reading* newReading, PyObject *element)
{
	if (!newReading)
		return;
	
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
		const char *ts_str = PyUnicode_AsUTF8(ts);
		newReading->setTimestamp(ts_str);
	}

	// Get 'user_ts' value: borrowed reference.
	PyObject* uts = PyDict_GetItemString(element, "timestamp");
	if (uts)
	{
		// Convert a timestamp of the from 2019-01-07 19:06:35.366100+01:00
		const char *ts_str = PyUnicode_AsUTF8(uts);
		newReading->setUserTimestamp(ts_str);
	}
	
	// Get 'uuid' value: borrowed reference.
	PyObject* uuid = PyDict_GetItemString(element, "key");
	if (uuid && PyUnicode_Check(uuid))
	{
		// Set uuid
		newReading->setUuid(std::string(PyUnicode_AsUTF8(uuid)));
	}
}

/**
 * Parse single reading element
 *
 * @param reading	Python dict object representing a reading
 * @param assetName	Asset name for the reading object
 */
Reading* Py2C_parseReadingElement(PyObject *reading, std::string assetName)
{
	// Fetch all Datapoints in 'reading' dict			
	PyObject *dKey, *dValue;  // borrowed references set by PyDict_Next()
	Py_ssize_t dPos = 0;
	Reading* newReading = NULL;

	if (!reading || !PyDict_Check(reading))
		return NULL;

	while (PyDict_Next(reading, &dPos, &dKey, &dValue))
	{
		DatapointValue* dataPoint;
		if (PyLong_Check(dValue) || PyFloat_Check(dValue) || PyBytes_Check(dValue) || PyUnicode_Check(dValue))
		{
			dataPoint = Py2C_createBasicDPV(dValue);
		}
		else if (PyList_Check(dValue))
		{
			dataPoint = Py2C_createListDPV(dValue);
		}
		else if (PyDict_Check(dValue))
		{
			dataPoint = Py2C_createDictDPV(dValue);
		}
		else
		{
			Logger::getLogger()->info("Unable to parse dValue in readings dict: dKey=%s, Py_TYPE(dValue)=%s", std::string(PyUnicode_AsUTF8(dKey)).c_str(), (Py_TYPE(dValue))->tp_name);
			return NULL;
		}

		// Add / Update the new Reading data			
		if (newReading == NULL)
		{
			if (dataPoint == NULL)
			{
				Logger::getLogger()->info("%s:%d: dataPoint is NULL", __FUNCTION__, __LINE__);
				continue;
			}
			newReading = new Reading(assetName,
							new Datapoint(std::string(PyUnicode_AsUTF8(dKey)),
								*dataPoint));
		}
		else
		{
			if (dataPoint == NULL)
			{
				Logger::getLogger()->info("%s:%d: dataPoint is NULL", __FUNCTION__, __LINE__);
				continue;
			}
			newReading->addDatapoint(new Datapoint(std::string(PyUnicode_AsUTF8(dKey)),
										*dataPoint));
		}

		// Remove temp objects
		delete dataPoint;
	}
	return newReading;
}

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

	// Get 'asset_code' value: borrowed reference.
	PyObject* assetCode = PyDict_GetItemString(element,
						   "asset");
	if (!assetCode)
	{
		Logger::getLogger()->info("Couldn't get 'asset' field from Python reading object");
		return NULL;
	}
	
	std::string assetName(PyUnicode_AsUTF8(assetCode));
	
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

	Reading* newReading = Py2C_parseReadingElement(reading, assetName);
	if (newReading)
		setReadingAttr(newReading, element);
	
	return newReading;
}

/**
 * Creating Reading objects from Python object
 *
 * @param element	Python Object (list)
 * @return		Pointer to a vector containing reading objects
 *				or NULL in case of error
 */
std::vector<Reading *>* Py2C_parseReadingListObject(PyObject *element)
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
	if (!assetCode)
	{
		Logger::getLogger()->info("Couldn't get 'asset' field from Python reading object");
		return NULL;
	}
	
	std::string assetName(PyUnicode_AsUTF8(assetCode));
	
	// Get 'reading' value: borrowed reference.
	PyObject* reading = PyDict_GetItemString(element,
							"readings");

	if (!assetCode || !reading || !PyList_Check(reading))
	{
		// Failure
		if (PyErr_Occurred())
		{
			logErrorMessage();
		}
		return NULL;
	}

	std::vector<Reading *>* vec = new std::vector<Reading *>();
	Reading* newReading;
	// Iterate reading objects in the list
	for (int i = 0; i < PyList_Size(reading); i++)
	{
		newReading = NULL;
		PyObject* elem = PyList_GetItem(reading, i);
		if (!elem)
		{
			// Failure
			if (PyErr_Occurred())
			{
				logErrorMessage();
			}
			delete vec;
			return NULL;
		}
		
		Reading* newReading = Py2C_parseReadingElement(elem, assetName);
		
		if (!newReading)
			continue;

		setReadingAttr(newReading, element);

		if (newReading)
		{
			vec->push_back(newReading);
		}
	}
	
	return vec;
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
			Reading* newReading = Py2C_parseReadingObject(element);
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
				newReadings = Py2C_parseReadingListObject(polledData);
			}
			else // just a single reading, no list
			{
				Reading* newReading = Py2C_parseReadingObject(polledData);
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
};

