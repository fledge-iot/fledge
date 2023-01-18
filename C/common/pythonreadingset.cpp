/*
 * Fledge Python Reading Set
 *
 * Copyright (c) 2021 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <pythonreadingset.h>
#include <pythonreading.h>
#include <stdexcept>

using namespace std;


/**
 * Set id, uuid, ts and user_ts in the reading object
 *
 * @param newReading	Reading object to update
 * @param readingList	PyObject containing this reading object
 * @param fillIfMissing	If True, only fill ID/TS fields if not set already
 */
void PythonReadingSet::setReadingAttr(Reading* newReading, PyObject *readingList, bool fillIfMissing)
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
		// Convert a timestamp of the form '2019-01-07 19:06:35.366100+01:00'
		const char *ts_str = PyUnicode_AsUTF8(ts);
		newReading->setTimestamp(ts_str);
	}

	// Get 'user_ts' value: borrowed reference.
	PyObject* uts = PyDict_GetItemString(readingList, "timestamp");
	fill = (!fillIfMissing || (fillIfMissing && newReading->getUserTimestamp()==0));
	if (fill && uts)
	{
		// Convert a timestamp of the form '2019-01-07 19:06:35.366100+01:00'
		const char *ts_str = PyUnicode_AsUTF8(uts);
		newReading->setUserTimestamp(ts_str);
	}
	
	// Get 'ts' value: borrowed reference.
	PyObject* userts = PyDict_GetItemString(readingList, "user_ts");
	fill = (!fillIfMissing || (fillIfMissing && newReading->getUserTimestamp()==0));
	if (fill && userts)
	{
		// Convert a timestamp of the form '2019-01-07 19:06:35.366100+01:00'
		const char *ts_str = PyUnicode_AsUTF8(userts);
		newReading->setUserTimestamp(ts_str);
	}

	// if User TS is still not filled, copy TS into it
	fill = (fillIfMissing && newReading->getUserTimestamp()==0);
	//Logger::getLogger()->debug("fill=%s, newReading->getUserTimestamp()=%d, newReading->getTimestamp()=%d", fill?"True":"False", newReading->getUserTimestamp(), newReading->getTimestamp());
	if (fill)
	{
		struct timeval tVal;
		newReading->getTimestamp(&tVal);
		newReading->setUserTimestamp(tVal);
		Logger::getLogger()->debug("Copied TS into user TS: newReading->getUserTimestamp()=%d", newReading->getUserTimestamp());
	}

	// if TS is still not filled, copy User TS into it
	fill = (fillIfMissing && newReading->getTimestamp()==0);
	//Logger::getLogger()->debug("fill=%s, newReading->getUserTimestamp()=%d, newReading->getTimestamp()=%d", fill?"True":"False", newReading->getUserTimestamp(), newReading->getTimestamp());
	if (fill)
	{
		struct timeval tVal;
		newReading->getUserTimestamp(&tVal);
		newReading->setTimestamp(tVal);
		Logger::getLogger()->debug("Copied user TS into TS: newReading->getUserTimestamp()=%d", newReading->getUserTimestamp());
	}
}


/**
 * Construct PythonReadingSet from a python list object that contains a
 * list of readings
 *
 * @param set	A Python object pointer that contians a list of readings
 */
PythonReadingSet::PythonReadingSet(PyObject *set)
{
	if (PyList_Check(set))
	{
		Logger::getLogger()->debug("PythonReadingSet c'tor: LIST of size %d", PyList_Size(set));
	}
	else if (PyDict_Check(set))
	{
		Logger::getLogger()->debug("PythonReadingSet c'tor: DICT of size %d", PyDict_Size(set));
	}
    
	if (PyList_Check(set))
	{
		Py_ssize_t listSize = PyList_Size(set);
		for (Py_ssize_t i = 0; i < listSize; i++)
		{
			PyObject *pyReading = PyList_GetItem(set, i);
			PythonReading *reading = new PythonReading(pyReading);
			setReadingAttr(reading, set, true);
			m_readings.push_back(reading);
			m_count++;
			m_last_id = reading->getId();
		}
	}
	else if (PyDict_Check(set))
	{
		PythonReading *reading = new PythonReading(set);
		if (reading)
		{
			setReadingAttr(reading, set, true);
			m_readings.push_back(reading);
			m_count++;
			m_last_id = reading->getId();
		}
	}
	else
	{
		Logger::getLogger()->error("Expected a Python list/dict as a reading set when constructing a PythonReadingSet");
		throw runtime_error("Expected a Python list/dict as a reading set when constructing a PythonReadingSet");
	}
}
    

/**
 * Convert the ReadingSet to a Python List
 *
 * @return A Python object that contains the set of readings as a Python list
 */
PyObject *PythonReadingSet::toPython(bool changeKeys)
{
	PyObject *set = PyList_New(m_readings.size());
	for (int i = 0; i < m_readings.size(); i++)
	{
		PythonReading *pyReading = (PythonReading *) m_readings[i];
		PyList_SetItem(set, i, pyReading->toPython(changeKeys));
	}
	return set;
}

