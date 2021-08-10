#include <pythonreading.h>
#include <stdexcept>

using namespace std;


PythonReading::PythonReading(PyObject *pyReading)
{
	// Get 'asset_code' value: borrowed reference.
	PyObject *assetCode = PyDict_GetItemString(pyReading,
						   "asset_code");
	// Get 'reading' value: borrowed reference.
	PyObject *reading = PyDict_GetItemString(pyReading,
						 "reading");
	// Keys not found or reading is not a dict
	if (!assetCode ||
	    !reading ||
	    !PyDict_Check(reading))
	{
		// Failure
		if (PyErr_Occurred())
		{
			throw runtime_error(errorMessage());
		}
	}
	m_asset = PyBytes_AsString(assetCode);

	// Fetch all Datapoints in 'reading' dict			
	PyObject *dKey, *dValue;
	Py_ssize_t dPos = 0;

	// Fetch all Datapoins in 'reading' dict
	// dKey and dValue are borrowed references
	while (PyDict_Next(reading, &dPos, &dKey, &dValue))
	{
		DatapointValue *dataPoint = NULL;
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
			string value = PyBytes_AsString(dValue);
			fixQuoting(value);
			dataPoint = new DatapointValue(value);
		}
		else if (PyUnicode_Check(dValue))
		{
			string value = PyUnicode_AsUTF8(dValue);
			fixQuoting(value);
			dataPoint = new DatapointValue(value);
		}
		else
		{
		}

		m_values.push_back(new Datapoint(string(PyBytes_AsString(dKey)), *dataPoint));

		/**
		  *Set id, uuid, ts and user_ts of the original data
		 */

		// Get 'id' value: borrowed reference.
		PyObject *id = PyDict_GetItemString(pyReading, "id");
		if (id && PyLong_Check(id))
		{
			// Set id
			m_id = PyLong_AsUnsignedLong(id);
		}

		// Get 'ts' value: borrowed reference.
		PyObject *ts = PyDict_GetItemString(pyReading, "ts");
		if (ts && PyLong_Check(ts))
		{
			// Set timestamp
			m_timestamp.tv_sec = PyLong_AsUnsignedLong(ts);
			m_timestamp.tv_usec = 0;
		}

		// Get 'user_ts' value: borrowed reference.
		PyObject *uts = PyDict_GetItemString(pyReading, "user_ts");
		if (uts && PyLong_Check(uts))
		{
			// Set user timestamp
			m_userTimestamp.tv_sec = PyLong_AsUnsignedLong(uts);
			m_userTimestamp.tv_usec = 0;
		}

		// Remove temp objects
		delete dataPoint;
	}
}

PyObject *PythonReading::toPython()
{
	// Create an object (dict) with 'asset_code' and 'readings' key
	PyObject *readingObject = PyDict_New();

	// Create object (dict) for reading Datapoints:
	// this will be added as vale for key 'readings'
	PyObject *newDataPoints = PyDict_New();

	// Get all datapoints
	for (auto it = m_values.begin(); it != m_values.end(); ++it)
	{
		PyObject *value;
		DatapointValue::dataTagType dataType = (*it)->getData().getType();

		if (dataType == DatapointValue::dataTagType::T_INTEGER)
		{
			value = PyLong_FromLong((*it)->getData().toInt());
		}
		else if (dataType == DatapointValue::dataTagType::T_FLOAT)
		{
			value = PyFloat_FromDouble((*it)->getData().toDouble());
		}
		else if (dataType == DatapointValue::dataTagType::T_STRING)
		{
			value = PyBytes_FromString((*it)->getData().toStringValue().c_str());
		}
		else if (dataType == DatapointValue::dataTagType::T_DATABUFFER)
		{
#if 0
			Py_buffer *buffer = (Py_buffer *)malloc(sizeof(Py_buffer));
			DataBuffer *dbuf = (*it)->getData().getDataBuffer();
			buffer->buf = dbuf->getData();
			buffer->itemsize = dbuf->m_itemSize;
			buffer->len = dbuf->len  *dbuf->itemSize;
#endif

		}
		else
		{
			value = PyBytes_FromString((*it)->getData().toString().c_str());
		}

		// Add Datapoint: key and value
		PyObject *key = PyBytes_FromString((*it)->getName().c_str());
		PyDict_SetItem(newDataPoints,
				key,
				value);
		
		Py_CLEAR(key);
		Py_CLEAR(value);
	}

	// Add reading datapoints
	PyDict_SetItemString(readingObject, "reading", newDataPoints);

	// Add reading asset name
	PyObject *assetVal = PyBytes_FromString(m_asset.c_str());
	PyDict_SetItemString(readingObject, "asset_code", assetVal);

	// Add reading id
	PyObject *readingId = PyLong_FromUnsignedLong(m_id);
	PyDict_SetItemString(readingObject, "id", readingId);

	// Add reading timestamp
	PyObject *readingTs = PyLong_FromUnsignedLong(m_timestamp.tv_sec);
	PyDict_SetItemString(readingObject, "ts", readingTs);

	// Add reading user timestamp
	PyObject *readingUserTs = PyLong_FromUnsignedLong(m_userTimestamp.tv_sec);
	PyDict_SetItemString(readingObject, "user_ts", readingUserTs);

	// Remove temp objects
	Py_CLEAR(newDataPoints);
	Py_CLEAR(assetVal);
	Py_CLEAR(readingId);
	Py_CLEAR(readingTs);
	Py_CLEAR(readingUserTs);
	
	return readingObject;
}

string PythonReading::errorMessage()
{
	//Get error message
	PyObject *pType, *pValue, *pTraceback;
	PyErr_Fetch(&pType, &pValue, &pTraceback);
	PyErr_NormalizeException(&pType, &pValue, &pTraceback);

	PyObject *str_exc_value = PyObject_Repr(pValue);
	PyObject *pyExcValueStr = PyUnicode_AsEncodedString(str_exc_value, "utf-8", "Error ~");

	// NOTE from :
	// https://docs.python.org/2/c-api/exceptions.html
	//
	// The value and traceback object may be NULL
	// even when the type object is not.	
	string errorMessage = pValue ?
				    PyBytes_AsString(pyExcValueStr) :
				    "no error description.";

	// Reset error
	PyErr_Clear();

	// Remove references
	Py_CLEAR(pType);
	Py_CLEAR(pValue);
	Py_CLEAR(pTraceback);
	Py_CLEAR(str_exc_value);
	Py_CLEAR(pyExcValueStr);

	return errorMessage;
}



/**
 * Fix the quoting if the datapoint contians unescaped quotes
 *
 * @param str	String to fix the quoting of
 */
void PythonReading::fixQuoting(string& str)
{
string newString;
bool escape = false;

	for (int i = 0; i < str.length(); i++)
	{
		if (str[i] == '\"' && escape == false)
		{
			newString += '\\';
			newString += '\\';
			newString += '\\';
		}
		else if (str[i] == '\\')
		{
			escape = !escape;
		}
		newString += str[i];
	}
	str = newString;
}
