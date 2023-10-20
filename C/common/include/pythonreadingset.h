#ifndef _PYTHON_READING_SET_H_
#define _PYTHON_READING_SET_H_
/*
 * Fledge Python Reading Set
 *
 * Copyright (c) 2021 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */

#include <reading_set.h>
#include <Python.h>

/**
 * A wrapper class for the ReadingSet class that allows conversion
 * to and from Python objects.
 */
class PythonReadingSet : public ReadingSet {
	public:
		PythonReadingSet(PyObject *pySet);
		~PythonReadingSet() {};
		PyObject	*toPython(bool changeKeys = false);
	private:
		void setReadingAttr(Reading* newReading, PyObject *readingList, bool fillIfMissing);
};
#endif
