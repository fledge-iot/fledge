/*
 * FogLAMP
 *
 * Copyright (c) 2019 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Amandeep Singh Arora
 */

#include <datapoint.h>

/*
 * FogLAMP
 *
 * Copyright (c) 2018 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch, Massimiliano Pinto
 */
#include <string>
#include <sstream>
#include <iomanip>
#include <cfloat>
#include <vector>


/**
 * Construct with an array of Datapoints
 */
DatapointValue::DatapointValue(std::vector<Datapoint*>*& values)
{
	m_value.dpa = values;
	m_type = T_DP_ARRAY;
}

/**
 * Copy constructor
 */
DatapointValue::DatapointValue(const DatapointValue& obj)
{
	m_type = obj.m_type;
	switch (m_type)
	{
	case T_STRING:
		m_value.str = new std::string(*(obj.m_value.str));
		break;
	case T_FLOAT_ARRAY:
		m_value.a = new std::vector<double>(*(obj.m_value.a));
		break;
	case T_DP_ARRAY:
		m_value.dpa = new std::vector<Datapoint*>(*(obj.m_value.dpa));
		break;
	default:
		m_value = obj.m_value;
		break;
	}
}

/**
 * Assignment Operator
 */
DatapointValue& DatapointValue::operator=(const DatapointValue& rhs)
{
	if (m_type == T_STRING)
	{
		// Remove previous value
		delete m_value.str;
	}
	if (m_type == T_FLOAT_ARRAY)
	{
		// Remove previous value
		delete m_value.a;
	}
	if (m_type == T_DP_ARRAY)
	{
		// Remove previous value
		delete m_value.dpa;
	}

	m_type = rhs.m_type;

	switch (m_type)
	{
	case T_STRING:
		m_value.str = new std::string(*(rhs.m_value.str));
		break;
	case T_FLOAT_ARRAY:
		m_value.a = new std::vector<double>(*(rhs.m_value.a));
		break;
	case T_DP_ARRAY:
		m_value.dpa = new std::vector<Datapoint*>(*(rhs.m_value.dpa));
		break;
	default:
		m_value = rhs.m_value;
		break;
	}

	return *this;
}

/**
 * Return the value as a string
 */
std::string	DatapointValue::toString() const
{
	std::ostringstream ss;

	switch (m_type)
	{
	case T_INTEGER:
		ss << m_value.i;
		return ss.str();
	case T_FLOAT:
	        ss << std::setprecision(DBL_DIG);
		ss << m_value.f;

		return ss.str();
	case T_FLOAT_ARRAY:
		ss << "[";
		for (auto it = m_value.a->begin();
		     it != m_value.a->end();
		     ++it)
		{
			if (it != m_value.a->begin())
			{
				ss << ", ";
			}
			ss << *it;
		}
		ss << "]";
		return ss.str();
	case T_DP_ARRAY:
		ss << "[";
		for (auto it = m_value.dpa->begin(); // std::vector<Datapoint *>*	dpa;
		     it != m_value.dpa->end();
		     ++it)
		{
			if (it != m_value.dpa->begin())
			{
				ss << ", ";
			}
			ss << "{";   /// dict doesn't need this, list needs it, need differentiation.
			ss << (*it)->toJSONProperty();
			ss << "}";
		}
		ss << "]";
		return ss.str();
	case T_STRING:
	default:
		ss << "\"";
		ss << *m_value.str;
		ss << "\"";
		return ss.str();
	}
}

