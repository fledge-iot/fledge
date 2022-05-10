#ifndef _PYTHONCONFIGCATEGORY_H
#define _PYTHONCONFIGCATEGORY_H
/*
 * Fledge Python Configuration Category
 *
 * Copyright (c) 2021 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */

#include <config_category.h>
#include <Python.h>

/**
 * A wrapper class for a ConfigCategory to convert to and from 
 * Python objects.
 */
class PythonConfigCategory : public ConfigCategory {
	public:
		PythonConfigCategory(PyObject *pyConfig);
		PyObject 		*toPython();
	private:
		PyObject 	*convertItem(CategoryItem *);
};
#endif
