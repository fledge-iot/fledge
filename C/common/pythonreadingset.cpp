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
 * Construct PythonRadingSet from a python list object that contains a
 * list of readings
 *
 * @param set	A Python object pointer that contians a list of readings
 */
PythonReadingSet::PythonReadingSet(PyObject *set)
{
	if (PyList_Check(set))
	{
		Py_ssize_t listSize = PyList_Size(set);
		for (Py_ssize_t i = 0; i < listSize; i++)
		{
			PyObject *pyReading = PyList_GetItem(set, i);
			PythonReading *reading = new PythonReading(pyReading);
			m_readings.push_back(reading);
			m_last_id = reading->getId();
		}
	}
	else
	{
		throw runtime_error("Expected a Python list as a reading set");
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
		PythonReading *pyReading = (PythonReading *)m_readings[i];
		PyList_SetItem(set, i, pyReading->toPython(changeKeys));
	}
	return set;
}
