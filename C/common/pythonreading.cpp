#include <pythonreading.h>
#include <stdexcept>

using namespace std;

bool PythonReading::doneNumPyImport = false;

/**
 * Construct a PythonReading from a DICT object returned by Pythin code.
 *
 * The PythonReading acts as a weapper on the Reading class to convert to and
 * from Readings in C and Python.
 *
 * @param pyReading	The Python DICT
 */
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
	if (PyUnicode_Check(assetCode))
	{
		m_asset = PyUnicode_AsUTF8(assetCode);
	}

	// Fetch all Datapoints in 'reading' dict			
	PyObject *dKey, *dValue;
	Py_ssize_t dPos = 0;

	// Fetch all Datapoins in 'reading' dict
	// dKey and dValue are borrowed references
	while (PyDict_Next(reading, &dPos, &dKey, &dValue))
	{
		DatapointValue *dataPoint = getDatapointValue(dValue);
		if (dataPoint)
		{
			m_values.push_back(new Datapoint(string(PyUnicode_AsUTF8(dKey)), *dataPoint));
			// Remove temp objects
			delete dataPoint;
		}
	}

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
}

/**
 */
DatapointValue *PythonReading::getDatapointValue(PyObject *value)
{
	DatapointValue *dataPoint = NULL;
	if (PyLong_Check(value) || PyLong_Check(value))
	{
		dataPoint = new DatapointValue((long)PyLong_AsUnsignedLongMask(value));
	}
	else if (PyFloat_Check(value))
	{
		dataPoint = new DatapointValue(PyFloat_AS_DOUBLE(value));
	}
	else if (PyBytes_Check(value))
	{
		string str = PyBytes_AsString(value);
		fixQuoting(str);
		dataPoint = new DatapointValue(str);
	}
	else if (PyUnicode_Check(value))
	{
		string str = PyUnicode_AsUTF8(value);
		fixQuoting(str);
		dataPoint = new DatapointValue(str);
	}
	else if (PyDict_Check(value))
	{
		vector<Datapoint *> *values = new vector<Datapoint *>;
		Py_ssize_t dPos = 0;
		PyObject *dKey, *dValue;
		while (PyDict_Next(value, &dPos, &dKey, &dValue))
		{
			DatapointValue *dpv = getDatapointValue(dValue);
			if (dpv)
			{
				values->push_back(new Datapoint(string(PyBytes_AsString(dKey)), *dpv));
				// Remove temp objects
				delete dpv;
			}
		}
		dataPoint = new DatapointValue(values, true);
	}
	else if (PyList_Check(value))
	{
		Py_ssize_t listSize = PyList_Size(value);
		// Find out what the list contains
		PyObject *item0 = PyList_GetItem(value, 0);
		if (item0 == NULL)
		{
			return NULL;
		}
		if (PyFloat_Check(item0))	// List of floats
		{
			vector<double> values;
			for (Py_ssize_t i = 0; i < listSize; i++)
			{
				double d = PyFloat_AS_DOUBLE(PyList_GetItem(value, i));
				values.push_back(d);
			}
			dataPoint = new DatapointValue(values);
		}
		else if (PyDict_Check(item0))
		{
			vector<Datapoint *>* values = new vector<Datapoint *>;
			for (Py_ssize_t i = 0; i < listSize; i++)
			{
				PyObject *item = PyList_GetItem(value, i);
				if (PyDict_Check(item))
				{
					PyObject *key, *val;
					PyDict_Next(item, 0, &key, &val);
					DatapointValue *dpv = getDatapointValue(val);
					if (dpv)
					{
						values->push_back(new Datapoint(string(PyBytes_AsString(key)), *dpv));
						// Remove temp objects
						delete dpv;
					}
				}
			}
			dataPoint = new DatapointValue(values, false);
		}
	}
	else if (PyArray_Check(value))
	{
		PyArrayObject *array = (PyArrayObject *)value;
		int item_size = PyArray_ITEMSIZE(array);
		if (PyArray_NDIM(array) == 1)	// It's a data buffer
		{
			npy_intp *dims = PyArray_DIMS(array);
			int n_items = (int)dims[0];

			// TODO get Data
		}
	}
	else	// TODO add other datapoint types
	{
		PyTypeObject *type = value->ob_type;
		Logger::getLogger()->error("Encountered an unsupported type '%s' when create a reading from Python", type->tp_name);
	}
	return dataPoint;
}

/**
 * Convert a PythonReading, which is just a Reading, into a PyObject
 * structure that can be passed to embedded Python code.
 *
 * @return PyObject*	The Python representation of the readings as a DICT
 */
PyObject *PythonReading::toPython()
{
	// Create object (dict) for reading Datapoints:
	// this will be added as the value for key 'readings'
	PyObject *dataPoints = PyDict_New();

	// Get all datapoints
	for (auto it = m_values.begin(); it != m_values.end(); ++it)
	{
		PyObject *value = convertDatapoint(*it);
		// Add Datapoint: key and value
		if (value)
		{
			PyObject *key = PyUnicode_FromString((*it)->getName().c_str());
			PyDict_SetItem(dataPoints, key, value);
		
			Py_CLEAR(key);
			Py_CLEAR(value);
		}
		else
		{
			Logger::getLogger()->info("Unable to covnert datapoint '%s' of reading '%s' tp Python",
					(*it)->getName().c_str(), m_asset.c_str());
		}
	}

	// Create an object (dict) with 'asset_code' and 'readings' key
	PyObject *readingObject = PyDict_New();

	// Add reading datapoints
	PyObject *key = PyUnicode_FromString("reading");
	PyDict_SetItem(readingObject, key, dataPoints);
	Py_CLEAR(key);

	// Add reading asset name
	PyObject *assetVal = PyUnicode_FromString(m_asset.c_str());
	key = PyUnicode_FromString("asset_code");
	PyDict_SetItem(readingObject, key, assetVal);
	Py_CLEAR(key);

	// Add reading id
	PyObject *readingId = PyLong_FromUnsignedLong(m_id);
	key = PyUnicode_FromString("id");
	PyDict_SetItem(readingObject, key, readingId);
	Py_CLEAR(key);

	// Add reading timestamp
	PyObject *readingTs = PyLong_FromUnsignedLong(m_timestamp.tv_sec);
	key = PyUnicode_FromString("ts");
	PyDict_SetItem(readingObject, key, readingTs);
	Py_CLEAR(key);

	// Add reading user timestamp
	PyObject *readingUserTs = PyLong_FromUnsignedLong(m_userTimestamp.tv_sec);
	key = PyUnicode_FromString("user_ts");
	PyDict_SetItem(readingObject, key, readingUserTs);
	Py_CLEAR(key);

	// Remove temp objects
	Py_CLEAR(dataPoints);
	Py_CLEAR(assetVal);
	Py_CLEAR(readingId);
	Py_CLEAR(readingTs);
	Py_CLEAR(readingUserTs);
	
	return readingObject;
}

PyObject *PythonReading::convertDatapoint(Datapoint *dp)
{
	PyObject *value = NULL;
	DatapointValue::dataTagType dataType = dp->getData().getType();

	if (dataType == DatapointValue::dataTagType::T_INTEGER)
	{
		value = PyLong_FromLong(dp->getData().toInt());
	}
	else if (dataType == DatapointValue::dataTagType::T_FLOAT)
	{
		value = PyFloat_FromDouble(dp->getData().toDouble());
	}
	else if (dataType == DatapointValue::dataTagType::T_STRING)
	{
		value = PyUnicode_FromString(dp->getData().toStringValue().c_str());
	}
	else if (dataType == DatapointValue::dataTagType::T_FLOAT_ARRAY)
	{
		vector<double>* values = dp->getData().getDpArr();;
		int i = 0;
		for (auto it = values->begin(); it != values->end(); ++it)
		{
			value = PyList_New(values->size());
			PyList_SetItem(value, i++, PyFloat_FromDouble(*it));
		}
	}
	else if (dataType == DatapointValue::dataTagType::T_DATABUFFER)
	{
		InitNumPy();
		DataBuffer *dbuf = dp->getData().getDataBuffer();
		npy_intp dim = dbuf->getItemCount();
		enum NPY_TYPES	type;
		switch (dbuf->getItemSize())
		{
			case 1:
				type = NPY_BYTE;
				break;
			case 2:
				type = NPY_INT16;
				break;
			case 4:
				type = NPY_INT32;
				break;
			case 8:
				type = NPY_INT64;
				break;
			default:
				break;
		}
		value = PyArray_SimpleNewFromData(1, &dim, type, dbuf->getData());
#if 0
		Py_buffer *buffer = (Py_buffer *)malloc(sizeof(Py_buffer));
		DataBuffer *dbuf = (*it)->getData().getDataBuffer();
		buffer->buf = dbuf->getData();
		buffer->itemsize = dbuf->m_itemSize;
		buffer->len = dbuf->len  *dbuf->itemSize;
#endif

	}
	else if (dataType == DatapointValue::dataTagType::T_IMAGE)
	{
		InitNumPy();
		DPImage *image = dp->getData().getImage();
		npy_intp dim[2];
		dim[0] = image->getWidth();
		dim[1] = image->getHeight();
		enum NPY_TYPES	type;
		switch (image->getDepth())
		{
			case 8:
				type = NPY_BYTE;
				break;
			case 16:
				type = NPY_INT16;
				break;
			case 32:
				type = NPY_INT32;
				break;
			case 64:
				type = NPY_INT64;
				break;
			default:
				break;
		}
		value = PyArray_SimpleNewFromData(2, dim, type, image->getData());
	}
	else if (dataType == DatapointValue::dataTagType::T_DP_DICT)
	{
		vector<Datapoint *>* children = dp->getData().getDpVec();;
		for (auto child = children->begin(); child != children->end(); ++child)
		{
			value = PyDict_New();
			PyObject *childValue = convertDatapoint(*child);
			// Add Datapoint: key and value
			PyObject *key = PyUnicode_FromString((*child)->getName().c_str());
			PyDict_SetItem(value, key, childValue);
		
			Py_CLEAR(key);
			Py_CLEAR(childValue);
		}
	}
	else if (dataType == DatapointValue::dataTagType::T_DP_LIST)
	{
		vector<Datapoint *>* children = dp->getData().getDpVec();
		int i = 0;
		for (auto child = children->begin(); child != children->end(); ++child)
		{
			value = PyList_New(children->size());
			PyObject *childValue = convertDatapoint(*child);
			// TODO complete
			// Add Datapoint: key and value
			PyObject *key = PyUnicode_FromString((*child)->getName().c_str());
			PyObject *dict = PyDict_New();
			PyDict_SetItem(dict, key, childValue);
			PyList_SetItem(value, i++, dict);
		
			Py_CLEAR(key);
			Py_CLEAR(childValue);
			Py_CLEAR(dict);
		}
	}
	else
	{
		Logger::getLogger()->info("Unable to convert datapoint tyoe '%s' to Python, defaulting to string representation", dp->getData().getTypeStr().c_str());
		value = PyUnicode_FromString(dp->getData().toString().c_str());
	}

	return value;
}

/**
 * Retrieve the error message last raised in Python
 *
 * @return string	The Python error message
 */
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
 * Fix the quoting if the datapoint contains unescaped quotes
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
