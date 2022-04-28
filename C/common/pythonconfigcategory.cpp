/*
 * Fledge Python Config Category
 *
 * Copyright (c) 2021 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <pythonconfigcategory.h>
#include <logger.h>
#include <stdexcept>


using namespace std;

/**
 * Construct a PythonConfigCategory from a DICT object returned by Python code.
 *
 * The PythonConfigCategory acts as a wrapper on the ConfigCategory class to convert to and
 * from configuration categories in C and Python.
 *
 * @param pyConfig	The Python DICT
 */
PythonConfigCategory::PythonConfigCategory(PyObject *config)
{
	if (!PyDict_Check(config))
	{
			throw runtime_error("Invalid configuration category, expected Python DICT");
	}

	// Fetch all items in configuration dict			
	PyObject *dKey, *dValue;
	Py_ssize_t dPos = 0;

	// Fetch all Datapoints in 'reading' dict
	// dKey and dValue are borrowed references
	while (PyDict_Next(config, &dPos, &dKey, &dValue))
	{
		string name = PyUnicode_AsUTF8(dKey);
		string description, type, def, value;
		if (!PyDict_Check(dValue))
		{
			Logger::getLogger()->error("Configuration item %s is not an object", name.c_str());
			throw runtime_error("Malformed configuration item");
		}
		PyObject *obj = PyDict_GetItemString(dValue, "description");
		if (obj)
		{
			description = PyUnicode_AsUTF8(obj);
		}
		else
		{
			Logger::getLogger()->error("Configuration item %s is missing a description", name.c_str());
			throw runtime_error("Malformed configuration item, missing description");
		}
		obj = PyDict_GetItemString(dValue, "type");
		if (obj)
		{
			type = PyUnicode_AsUTF8(obj);
		}
		else
		{
			Logger::getLogger()->error("Configuration item %s is missing a type", name.c_str());
			throw runtime_error("Malformed configuration item, missing type");
		}
		obj = PyDict_GetItemString(dValue, "default");
		if (obj)
		{
			def = PyUnicode_AsUTF8(obj);
		}
		else
		{
			Logger::getLogger()->error("Configuration item %s is missing a default value", name.c_str());
			throw runtime_error("Malformed configuration item, missing default value");
		}
		if (type.compare("enumeration") == 0)
		{
			vector<string> options;
			obj = PyDict_GetItemString(dValue, "options");
			if (obj && PyList_Check(obj))
			{
				Py_ssize_t listSize = PyList_Size(obj);
				for (Py_ssize_t i = 0; i < listSize; i++)
				{
					PyObject *str = PyList_GetItem(obj, i);
					string s = PyUnicode_AsUTF8(str);
					options.push_back(s);
				}

				addItem(name, description, def, value, options);
			}
			else
			{
				Logger::getLogger()->error("Configuration item %s is missing an options list", name.c_str());
				throw runtime_error("Malformed configuration item, missing options");
			}
		}
		else
		{
			addItem(name, description, type, def, value);
		}
	}
}

/**
 * Convert a ConfigCategory, into a PyObject
 * structure that can be passed to embedded Python code.
 *
 * @return PyObject*	The Python representation of the configuration category as a DICT
 */
PyObject *PythonConfigCategory::toPython()
{
	// Create object (dict) for reading Datapoints:
	// this will be added as the value for key 'readings'
	PyObject *category = PyDict_New();

	// Get all datapoints
	for (auto it = m_items.begin(); it != m_items.end(); ++it)
	{
		PyObject *value = convertItem(*it);
		// Add Item: key and value
		if (value)
		{
			PyObject *key = PyUnicode_FromString((*it)->m_name.c_str());
			PyDict_SetItem(category, key, value);
		
			Py_CLEAR(key);
			Py_CLEAR(value);
		}
		else
		{
			Logger::getLogger()->info("Unable to convert configuration item '%s' of configuration category '%s' to Python",
					(*it)->m_name.c_str(), m_name.c_str());
		}
	}

	return category;
}

/**
 * Convert a single datapoint into a Pythn object
 *
 * @param dp	The datapoint to convert
 * @return The pointer to a converted Python Object or NULL if the conversion failed
 */
PyObject *PythonConfigCategory::convertItem(CategoryItem *item)
{
	PyObject *pyItem = PyDict_New();

	PyObject *value = PyUnicode_FromString(item->m_displayName.c_str());
	PyObject *key = PyUnicode_FromString("displayName");
	PyDict_SetItem(pyItem, key, value);
	Py_CLEAR(key);
	Py_CLEAR(value);

	value = PyUnicode_FromString(item->m_type.c_str());
	key = PyUnicode_FromString("type");
	PyDict_SetItem(pyItem, key, value);
	Py_CLEAR(key);
	Py_CLEAR(value);

	value = PyUnicode_FromString(item->m_default.c_str());
	key = PyUnicode_FromString("default");
	PyDict_SetItem(pyItem, key, value);
	Py_CLEAR(key);
	Py_CLEAR(value);

	value = PyUnicode_FromString(item->m_value.c_str());
	key = PyUnicode_FromString("value");
	PyDict_SetItem(pyItem, key, value);
	Py_CLEAR(key);
	Py_CLEAR(value);

	if (item->m_description.length())
	{
		value = PyUnicode_FromString(item->m_description.c_str());
		key = PyUnicode_FromString("description");
		PyDict_SetItem(pyItem, key, value);
		Py_CLEAR(key);
		Py_CLEAR(value);
	}

	if (item->m_order.length())
	{
		value = PyUnicode_FromString(item->m_order.c_str());
		key = PyUnicode_FromString("order");
		PyDict_SetItem(pyItem, key, value);
		Py_CLEAR(key);
		Py_CLEAR(value);
	}

	if (item->m_readonly.length())
	{
		value = PyUnicode_FromString(item->m_readonly.c_str());
		key = PyUnicode_FromString("readonly");
		PyDict_SetItem(pyItem, key, value);
		Py_CLEAR(key);
		Py_CLEAR(value);
	}

	if (item->m_mandatory.length())
	{
		value = PyUnicode_FromString(item->m_mandatory.c_str());
		key = PyUnicode_FromString("mandatory");
		PyDict_SetItem(pyItem, key, value);
		Py_CLEAR(key);
		Py_CLEAR(value);
	}

	if (item->m_deprecated.length())
	{
		value = PyUnicode_FromString(item->m_deprecated.c_str());
		key = PyUnicode_FromString("deprecated");
		PyDict_SetItem(pyItem, key, value);
		Py_CLEAR(key);
		Py_CLEAR(value);
	}

	if (item->m_length.length())
	{
		value = PyUnicode_FromString(item->m_length.c_str());
		key = PyUnicode_FromString("length");
		PyDict_SetItem(pyItem, key, value);
		Py_CLEAR(key);
		Py_CLEAR(value);
	}

	if (item->m_minimum.length())
	{
		value = PyUnicode_FromString(item->m_minimum.c_str());
		key = PyUnicode_FromString("minimum");
		PyDict_SetItem(pyItem, key, value);
		Py_CLEAR(key);
		Py_CLEAR(value);
	}

	if (item->m_maximum.length())
	{
		value = PyUnicode_FromString(item->m_maximum.c_str());
		key = PyUnicode_FromString("maximum");
		PyDict_SetItem(pyItem, key, value);
		Py_CLEAR(key);
		Py_CLEAR(value);
	}

	if (item->m_filename.length())
	{
		value = PyUnicode_FromString(item->m_filename.c_str());
		key = PyUnicode_FromString("filename");
		PyDict_SetItem(pyItem, key, value);
		Py_CLEAR(key);
		Py_CLEAR(value);
	}


	return pyItem;
}

