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
		Logger::getLogger()->warn("Unable to parse dValue: Py_TYPE(dValue)=%s", (Py_TYPE(dValue))->tp_name);
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
		else if (PyObject_CheckBuffer(dValue))
		{
			Logger *logger = Logger::getLogger();
			logger->warn("Object %s supports buffer protocol %s",  std::string(PyUnicode_AsUTF8(dKey)).c_str());
			Py_buffer view;
			int flags = 0;
			PyObject_GetBuffer(dValue, &view, flags);

			logger->warn("Buffer is %d long, item size %d format %s", view.len, view.itemsize, view.format);

			PyBuffer_Release(&view);
		}
		else
		{
			Logger::getLogger()->warn("Unable to parse dValue in 'data' dict: dKey=%s, Py_TYPE(dValue)=%s", std::string(PyUnicode_AsUTF8(dKey)).c_str(), (Py_TYPE(dValue))->tp_name);
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
	
	// Get 'ts' value: borrowed reference.
	PyObject* userts = PyDict_GetItemString(element, "user_ts");
	if (userts)
	{
		// Convert a timestamp of the from 2019-01-07 19:06:35.366100+01:00
		const char *ts_str = PyUnicode_AsUTF8(userts);
		newReading->setUserTimestamp(ts_str);
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
		else if (PyObject_CheckBuffer(dValue))
		{
			Logger *logger = Logger::getLogger();
			logger->warn("Object %s supports buffer protocol",  std::string(PyUnicode_AsUTF8(dKey)).c_str());
			Py_buffer view;
			int flags = PyBUF_SIMPLE;
			if (PyObject_GetBuffer(dValue, &view, flags) == 0)
			{
				logger->warn("Buffer is %d long, item size %d format %s, %d dimensions", view.len, view.itemsize, view.format, view.ndim);
				for (int i = 0; i < view.ndim; i++)
					logger->warn("Dimension: %d is %d", i, view.shape[i]);
				PyBuffer_Release(&view);
			}
			else
				logger->error("Failed to get buffer");
		}
		else
		{
			Logger::getLogger()->debug("Unable to parse dValue in readings dict: dKey=%s, Py_TYPE(dValue)=%s", std::string(PyUnicode_AsUTF8(dKey)).c_str(), (Py_TYPE(dValue))->tp_name);
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
		PyObject* readingObject = PyDict_New();

		// Create object (dict) for reading Datapoints:
		// this will be added as value for key 'readings'
		PyObject* newDataPoints = PyDict_New();

		// Get all datapoints
		std::vector<Datapoint *>& dataPoints = (*elem)->getReadingData();
		for (auto it = dataPoints.begin(); it != dataPoints.end(); ++it)
		{
			PyObject* value;
			DatapointValue::dataTagType dataType = (*it)->getData().getType();

			if (dataType == DatapointValue::dataTagType::T_INTEGER)
			{
				value = PyLong_FromLong((*it)->getData().toInt());
			}
			else if (dataType == DatapointValue::dataTagType::T_FLOAT)
			{
				value = PyFloat_FromDouble((*it)->getData().toDouble());
			}
			else
			{
				// strip enclosing double-quotes, if present, when passing string from C to Python
				if (dataType == DatapointValue::dataTagType::T_STRING)
				{
					std::string s((*it)->getData().toString().c_str());
					std::string s2;
					if(s[0]=='"')
						s2 = s.substr(1, s.size()-2);
					else
						s2 = s;

					value = PyUnicode_FromString(s2.c_str());
				}
				else  // non-string, possibly nested object
					value = PyUnicode_FromString((*it)->getData().toString().c_str());
			}

			// Add Datapoint: key and value
			PyObject* key = PyUnicode_FromString((*it)->getName().c_str());
			PyDict_SetItem(newDataPoints,
					key,
					value);
			
			Py_CLEAR(key);
			Py_CLEAR(value);
		}

		// Add reading datapoints
		if (changeDictKeys)
			PyDict_SetItemString(readingObject, "reading", newDataPoints);
		else
			PyDict_SetItemString(readingObject, "readings", newDataPoints);

		// Add reading asset name
		PyObject* assetVal = PyUnicode_FromString((*elem)->getAssetName().c_str());

		if (changeDictKeys)
			PyDict_SetItemString(readingObject, "asset_code", assetVal);
		else
			PyDict_SetItemString(readingObject, "asset", assetVal);

		/**
		 * Set id, uuid, timestamp and user_timestamp
		 */

		// Add reading id
		PyObject* readingId = PyLong_FromUnsignedLong((*elem)->getId());
		PyDict_SetItemString(readingObject, "id", readingId);

		// Add reading timestamp
		//PyObject* readingTs = PyLong_FromUnsignedLong((*elem)->getTimestamp());
		PyObject* readingTs =
			PyUnicode_FromString(((*elem)->getAssetDateTime(Reading::FMT_DEFAULT) + "+00:00").c_str());
		PyDict_SetItemString(readingObject, "ts", readingTs);

		// Add reading user timestamp
		//PyObject* readingUserTs = PyLong_FromUnsignedLong((*elem)->getUserTimestamp());
		PyObject* readingUserTs =
			PyUnicode_FromString(((*elem)->getAssetDateUserTime(Reading::FMT_DEFAULT) + "+00:00").c_str());
		PyDict_SetItemString(readingObject, "user_ts", readingUserTs);

		// Add new object to the list
		PyList_Append(readingsList, readingObject);

		// Remove temp objects
		Py_CLEAR(newDataPoints);
		Py_CLEAR(assetVal);
		Py_CLEAR(readingId);
		Py_CLEAR(readingTs);
		Py_CLEAR(readingUserTs);
		Py_CLEAR(readingObject);
	}

	// Return pointer of new allocated list
	return readingsList;
}
}; // End of extern C
