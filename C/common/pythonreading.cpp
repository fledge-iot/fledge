/*
 * Fledge Python Reading
 *
 * Copyright (c) 2021 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 *
 * Extreme caution needs to be taken with these Python interfaces
 * classes, especially with the use of numpy which is not written
 * to support multiple imports of the package due to the use
 * of global variables within numpy itself. Hence we import numpy
 * once by use of the import_array() macro. This macro also has
 * issues a it contians an embedded return statement.
 */
#include <pythonreading.h>
#include <pyruntime.h>
#include <stdexcept>

#define PY_ARRAY_UNIQUE_SYMBOL  PyArray_API_FLEDGE
#include <numpy/npy_common.h>
#define NPY_NO_DEPRECATED_API NPY_1_7_API_VERSION
#include <numpy/ndarraytypes.h>
#include <numpy/ndarrayobject.h>

#undef NUMPY_IMPORT_ARRAY_RETVAL
#define NUMPY_IMPORT_ARRAY_RETVAL       0

bool PythonReading::doneNumPyImport = false;

using namespace std;


/**
 * Construct a PythonReading from a DICT object returned by Python code.
 *
 * The PythonReading acts as a wrapper on the Reading class to convert to and
 * from Readings in C and Python.
 *
 * @param pyReading	The Python DICT
 */
PythonReading::PythonReading(PyObject *pyReading)
{    
	// Get 'asset_code' value: borrowed reference.
	PyObject *assetCode = PyDict_GetItemString(pyReading,
						   "asset");

	if (!assetCode)
	{
		assetCode = PyDict_GetItemString(pyReading, "asset_code");
	}

	// Get 'reading' value: borrowed reference.
	PyObject *reading = PyDict_GetItemString(pyReading,
						 "readings");
	if (!reading)
	{
		reading = PyDict_GetItemString(pyReading, "reading");
	}

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
		if (!assetCode)
			throw runtime_error("Reading has no asset code element.");
		if (!reading)
			throw runtime_error("Reading is missing the reading element which shuld contain the data.");
		else
			throw runtime_error("The reading element in the python Reading is of an incorrect type, it should be a Python DICT.");
	}
	if (PyUnicode_Check(assetCode))
	{
		m_asset = PyUnicode_AsUTF8(assetCode);
	}
	else if (PyBytes_Check(assetCode))
	{
		m_asset = PyBytes_AsString(assetCode);
	}
	else
	{
		throw runtime_error("Unable to parse the asset code value. Asset codes should be a string");

	}

	// Fetch all Datapoints in 'reading' dict			
	PyObject *dKey, *dValue;
	Py_ssize_t dPos = 0;

	// Fetch all Datapoints in 'readings' dict
	// dKey and dValue are borrowed references
	while (PyDict_Next(reading, &dPos, &dKey, &dValue))
	{
		DatapointValue *dataPoint = getDatapointValue(dValue);
		if (dataPoint)
		{
			// Deteck Python keys like reading[b'ema']
			// or reading['ema']
			if (PyUnicode_Check(dKey))   
			{
				m_values.emplace_back(new Datapoint(
					string(PyUnicode_AsUTF8(dKey)),
					*dataPoint));
			}
			else
			{
				m_values.emplace_back(new Datapoint(
					string(PyBytes_AsString(dKey)),
					*dataPoint));
			}

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
		m_has_id = true;
	}
	else
	{
		m_has_id = false;
		m_id = 0;
	}

	// New reference, to delete
	PyObject *key = PyUnicode_FromString("timestamp");

	// Get 'ts' value: borrowed reference.
	// Need to use PyDict_GetItemWithError in order to avoid an exception
	PyObject *ts = PyDict_GetItemWithError(pyReading, key);
	if (!(ts && PyUnicode_Check(ts)))
	{
		ts = PyDict_GetItemString(pyReading, "ts");
	}
	if (ts && PyUnicode_Check(ts))
	{
		// Set timestamp
		const char *ts_str = PyUnicode_AsUTF8(ts);
		setTimestamp(ts_str);
	}
	else
	{
		m_timestamp.tv_sec = 0;
		m_timestamp.tv_usec = 0;
		// Logger::getLogger()->debug("PythonReading c'tor: Couldn't parse 'ts' ");
	}

	Py_CLEAR(key);

	// New reference, to delete
	key = PyUnicode_FromString("user_ts");

	// Get 'user_ts' value: borrowed reference.
	PyObject *uts = PyDict_GetItemWithError(reading, key);
	if (!uts)
	{
		uts = PyDict_GetItemWithError(pyReading, key);
	}
	if (uts && PyUnicode_Check(uts))
	{
		// Set user timestamp
		const char *ts_str = PyUnicode_AsUTF8(uts);
		setUserTimestamp(ts_str);
	}
	else
	{
		//Logger::getLogger()->debug("PythonReading c'tor: Couldn't parse 'user_ts' ");
	        m_userTimestamp.tv_sec = 0;
       		m_userTimestamp.tv_usec = 0;
	}
	Py_CLEAR(key);
}

/**
 * Given a Python value convert it into a DatapointValue
 *
 * @param value The python object to convert
 * @return The converted DatapointValue or NULL if the conversion was not possible
 */
DatapointValue *PythonReading::getDatapointValue(PyObject *value)
{
	InitNumPy();
	if (!value)
	{
		throw runtime_error("NULL datapoint value in Python reading");
	}

	DatapointValue *dataPoint = NULL;
	if (PyLong_Check(value))	// Integer	T_INTEGER
	{
		dataPoint = new DatapointValue((long)PyLong_AsUnsignedLongMask(value));
	}
	else if (PyFloat_Check(value))		// Float		T_FLOAT
	{
		dataPoint = new DatapointValue(PyFloat_AS_DOUBLE(value));
	}
	else if (PyBytes_Check(value))		// String		T_STRING
	{
		string str = PyBytes_AsString(value);
		fixQuoting(str);
		dataPoint = new DatapointValue(str);
	}
	else if (PyUnicode_Check(value))	// String		T_STRING
	{
		string str = PyUnicode_AsUTF8(value);
		fixQuoting(str);
		dataPoint = new DatapointValue(str);
	}
	else if (PyDict_Check(value))		// Nested object	T_DP_DICT
	{
		vector<Datapoint *> *values = new vector<Datapoint *>;
		Py_ssize_t dPos = 0;
		PyObject *dKey, *dValue;
		while (PyDict_Next(value, &dPos, &dKey, &dValue))
		{
			DatapointValue *dpv = getDatapointValue(dValue);
			if (dpv)
			{
		               if (PyUnicode_Check(dKey))
                               {
                                     values->emplace_back(new Datapoint(string(PyUnicode_AsUTF8(dKey)), *dpv));
                               }
                               else
                               {
                                     values->emplace_back(new Datapoint(string(PyBytes_AsString(dKey)), *dpv));
                               }
				// Remove temp objects
				delete dpv;
			}
		}
		dataPoint = new DatapointValue(values, true);
	}
	else if (PyList_Check(value))	// List of data points or floats
	{
		Py_ssize_t listSize = PyList_Size(value);
		// Find out what the list contains
		PyObject *item0 = PyList_GetItem(value, 0);
		if (item0 == NULL)
		{
			return NULL;
		}
		if (PyFloat_Check(item0))	// List of floats	T_FLOAT_ARRAY
		{
			vector<double> values;
			for (Py_ssize_t i = 0; i < listSize; i++)
			{
				double d = PyFloat_AS_DOUBLE(PyList_GetItem(value, i));
				values.push_back(d);
			}
			dataPoint = new DatapointValue(values);
		}
		else if (PyList_Check(item0))	// 2D array 		T_2D_FLOAT_ARRAY
		{
			vector<vector<double>* > values;
			for (Py_ssize_t i = 0; i < listSize; i++)
			{
				vector<double> *row = new vector<double>;
				PyObject *pyRow = PyList_GetItem(value, i);
				for (Py_ssize_t j = 0; j < PyList_Size(pyRow); j++)
				{
					double d = PyFloat_AS_DOUBLE(PyList_GetItem(pyRow, j));
					row->push_back(d);
				}
				values.push_back(row);
			}
			dataPoint = new DatapointValue(values);
		}
		else if (PyDict_Check(item0))	// List of datapoints	T_DP_LIST
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
						values->emplace_back(new Datapoint(string(PyBytes_AsString(key)), *dpv));
						// Remove temp objects
						delete dpv;
					}
				}
			}
			dataPoint = new DatapointValue(values, false);
		}
	}
	else if (PyArray_Check(value))	// Numpy array
	{
		PyArrayObject *array = (PyArrayObject *)value;
		int item_size = PyArray_ITEMSIZE(array);
		if (PyArray_NDIM(array) == 1)	// Databuffer	T_DATABUFFER
		{
			npy_intp *dims = PyArray_DIMS(array);
			int n_items = (int)dims[0];
			DataBuffer *buffer = new DataBuffer(item_size, n_items);
			memcpy(buffer->getData(), PyArray_DATA(array), n_items * item_size);

			dataPoint = new DatapointValue(buffer);
		}
		else if (PyArray_NDIM(array) == 2)	// Image	T_IMAGE
		{
			npy_intp *dims = PyArray_DIMS(array);
			int height = (int)dims[0];
			int width = (int)dims[1];
			int depth = item_size * 8;	// In bits
			DPImage *image = new DPImage(width, height, depth, PyArray_DATA(array));

			dataPoint = new DatapointValue(image);
		}
		else if (PyArray_NDIM(array) == 3)	// RGB Image	T_IMAGE
		{
			npy_intp *dims = PyArray_DIMS(array);
			if ((int)dims[2] == 3)
			{
				int height = (int)dims[0];
				int width = (int)dims[1];
				int depth = 24;	// In bits
				DPImage *image = new DPImage(width, height, depth, PyArray_DATA(array));

				dataPoint = new DatapointValue(image);
			}
			else
			{
				Logger::getLogger()->error("Received 3D numpy array that is not RGB image");
			}
		}
		else
		{
			Logger::getLogger()->error("Encountered a numpy array with more than 3 dimensions in a Python data point %s. This is currently not supported");
		}
	}
	else
	{
        Logger::getLogger()->info("PythonReading::getDatapointValue: UNSUPPORTED");
		PyTypeObject *type = value->ob_type;
		Logger::getLogger()->error("Encountered an unsupported type '%s' when create a reading from Python", type->tp_name);
	}

	return dataPoint;
}

/**
 * Convert a PythonReading, which is just a Reading, into a PyObject
 * structure that can be passed to embedded Python code.
 *
 * @param changeKeys		Set DICT keys as reading/asset_code if true
 *				or readings/asset if false
 * @param useBytesString	Whether to use DICT keys as BytesString
 *				and string values as BytesString
 * @return PyObject*	The Python representation of the readings as a DICT
 */
PyObject *PythonReading::toPython(bool changeKeys, bool useBytesString)
{
	// Create object (dict) for reading Datapoints:
	// this will be added as the value for key 'readings'
	PyObject *dataPoints = PyDict_New();

	// Get all datapoints
	for (auto it = m_values.begin(); it != m_values.end(); ++it)
	{
		// Pass BytesString switch
		PyObject *value = convertDatapoint(*it, useBytesString);
		// Add Datapoint: key and value
		if (value)
		{
			PyObject *key = useBytesString ?
					PyBytes_FromString((*it)->getName().c_str())
					:
					PyUnicode_FromString((*it)->getName().c_str());
			PyDict_SetItem(dataPoints, key, value);
		
			Py_CLEAR(key);
			Py_CLEAR(value);
		}
		else
		{
			Logger::getLogger()->info("Unable to convert datapoint '%s' of reading '%s' tp Python",
					(*it)->getName().c_str(), m_asset.c_str());
		}
	}

	// Create an object (dict) with 'asset_code' and 'readings' key
	PyObject *readingObject = PyDict_New();

	// Add reading datapoints
	PyObject *key = PyUnicode_FromString(changeKeys ? "reading" : "readings");
	PyDict_SetItem(readingObject, key, dataPoints);
	Py_CLEAR(key);

	// Add reading asset name
	PyObject *assetVal = useBytesString ?
			PyBytes_FromString(m_asset.c_str())
			:
			PyUnicode_FromString(m_asset.c_str());

	key = PyUnicode_FromString(changeKeys ? "asset_code" : "asset");
	PyDict_SetItem(readingObject, key, assetVal);
	Py_CLEAR(key);

	// Add reading id
	PyObject *readingId = PyLong_FromUnsignedLong(m_id);
	key = PyUnicode_FromString("id");
	PyDict_SetItem(readingObject, key, readingId);
	Py_CLEAR(key);

	// Add reading timestamp
	// PyObject *readingTs = PyLong_FromUnsignedLong(m_timestamp.tv_sec);
	string s = this->getAssetDateTime(FMT_DEFAULT) + "+00:00";
	PyObject *readingTs = PyUnicode_FromString(s.c_str());
	key = PyUnicode_FromString("ts");
	PyDict_SetItem(readingObject, key, readingTs);
	Py_CLEAR(key);

	// Add reading user timestamp
	//PyObject *readingUserTs = PyLong_FromUnsignedLong(m_userTimestamp.tv_sec);
	s = this->getAssetDateUserTime(FMT_DEFAULT) + "+00:00";
	PyObject *readingUserTs = PyUnicode_FromString(s.c_str());
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

/**
 * Convert a single datapoint into a Pythn object
 *
 * @param dp		The datapoint to convert
 * @param bytesString	Wheter to set PyObject string as PyBytes or PyUnicode
 * @return The pointer to a converted Python Object or NULL if the conversion failed
 */
PyObject *PythonReading::convertDatapoint(Datapoint *dp, bool bytesString)
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
		value = bytesString ?
				PyBytes_FromString(dp->getData().toStringValue().c_str())
				:
				PyUnicode_FromString(dp->getData().toStringValue().c_str());
	}
	else if (dataType == DatapointValue::dataTagType::T_FLOAT_ARRAY)
	{
		vector<double>* values = dp->getData().getDpArr();;
		int i = 0;
		value = PyList_New(values->size());
		for (auto it = values->begin(); it != values->end(); ++it)
		{
			PyList_SetItem(value, i++, PyFloat_FromDouble(*it));
		}
	}
	else if (dataType == DatapointValue::dataTagType::T_2D_FLOAT_ARRAY)
	{
		vector<vector<double>* > *vec = dp->getData().getDp2DArr();
		value = PyList_New(vec->size());
		int rowNo = 0;
		for (auto row : *vec)
		{
			int i = 0;
			PyObject *pyRow = PyList_New(row->size());
			for (auto& d : *row)
			{
				PyList_SetItem(pyRow, i++, PyFloat_FromDouble(d));
			}
			PyList_SetItem(value, rowNo++, pyRow);
		}
	}
	else if (dataType == DatapointValue::dataTagType::T_DATABUFFER)
	{
//		PythonRuntime::getPythonRuntime()->initNumPy();
		InitNumPy();
		DataBuffer *dbuf = dp->getData().getDataBuffer();
		npy_intp dim = dbuf->getItemCount();
		enum NPY_TYPES	type;
		switch (dbuf->getItemSize())
		{
			case 1:
				type = NPY_UBYTE;
				break;
			case 2:
				type = NPY_UINT16;
				break;
			case 4:
				type = NPY_UINT32;
				break;
			case 8:
				type = NPY_UINT64;
				break;
			default:
				break;
		}
		PyGILState_STATE state = PyGILState_Ensure();
		value = PyArray_SimpleNewFromData(1, &dim, type, dbuf->getData());
		PyGILState_Release(state);
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
		//PythonRuntime::getPythonRuntime()->initNumPy();
		InitNumPy();
		DPImage *image = dp->getData().getImage();
		if (image->getDepth() == 24)
		{{
			npy_intp dim[3];
			dim[0] = image->getHeight();
			dim[1] = image->getWidth();
			dim[2] = 3;
			enum NPY_TYPES	type = NPY_UBYTE;
			PyGILState_STATE state = PyGILState_Ensure();
			value = PyArray_SimpleNewFromData(3, dim, type, image->getData());
			PyGILState_Release(state);
		}
		}
		else
		{
			npy_intp dim[2];
			dim[0] = image->getHeight();
			dim[1] = image->getWidth();
			enum NPY_TYPES	type;
			switch (image->getDepth())
			{
				case 8:
					type = NPY_UBYTE;
					break;
				case 16:
					type = NPY_UINT16;
					break;
				case 32:
					type = NPY_UINT32;
					break;
				case 64:
					type = NPY_UINT64;
					break;
				default:
					break;
			}
			PyGILState_STATE state = PyGILState_Ensure();
			value = PyArray_SimpleNewFromData(2, dim, type, image->getData());
			PyGILState_Release(state);
		}
	}
	else if (dataType == DatapointValue::dataTagType::T_DP_DICT)
	{
		vector<Datapoint *>* children = dp->getData().getDpVec();;
		value = PyDict_New();
		for (auto child = children->begin(); child != children->end(); ++child)
		{
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
		value = PyList_New(children->size());
		for (auto child = children->begin(); child != children->end(); ++child)
		{
			PyObject *childValue = convertDatapoint(*child);
			// TODO complete
			// Add Datapoint: key and value
			PyObject *key = PyUnicode_FromString((*child)->getName().c_str());
			PyObject *dict = PyDict_New();
			PyDict_SetItem(dict, key, childValue);
			PyList_SetItem(value, i++, dict);
		
			Py_CLEAR(key);
			Py_CLEAR(childValue);
		}
	}
	else
	{
		Logger::getLogger()->info("Unable to convert datapoint type '%s' to Python, defaulting to string representation", dp->getData().getTypeStr().c_str());
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
					
	Logger::getLogger()->error("Exception from python interpreter: %s", errorMessage.c_str());
	
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


/**
 * Return true of the Python object is an array. This is mostly for testing
 * and overcomes an issue with including the numpy header files multiple times.
 *
 * @param obj	The Pythin object to test
 * @return true if the Python object is a numpy array
 */
bool PythonReading::isArray(PyObject *obj)
{
	return PyArray_Check(obj);
}

/**
 * Import NumPy. Due to the way numpy uses global variables we must only do
 * this once in a single exeutable as multiple imports result in crashes.
 */
int PythonReading::InitNumPy()
{
	if (!PythonReading::doneNumPyImport)
	{
		PythonReading::doneNumPyImport = true;
		// Note the following is a macro in the numpy header file that has an embedded return
		// in the case of failure. Hence the need to return a value. Assume no code after this
		// line is run
		PyGILState_STATE state = PyGILState_Ensure();
		
		if (PyImport_ImportModule("numpy.core.multiarray") == NULL)
			throw runtime_error(errorMessage());

		import_array();
		
		PyGILState_Release(state);
	}
	return 0;
};


