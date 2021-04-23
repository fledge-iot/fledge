/*
 * Fledge
 *
 * Copyright (c) 2019 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Amandeep Singh Arora
 */

#include <string>
#include <sstream>
#include <iomanip>
#include <cfloat>
#include <vector>
#include <logger.h>
#include <datapoint.h>

 /**
 * Return the value as a string
 *
 * @return	String representing the DatapointValue object
 */
std::string DatapointValue::toString() const
{
	std::ostringstream ss;

	switch (m_type)
	{
	case T_INTEGER:
		ss << m_value.i;
		return ss.str();
	case T_FLOAT:
		{
			char tmpBuffer[100];
			std::string s;

			snprintf(tmpBuffer, sizeof(tmpBuffer), "%.10f", m_value.f);
			s= tmpBuffer;

			// remove trailing 0's
			if (s[s.size()-1]== '0') {
				s.erase(s.find_last_not_of('0') + 1, std::string::npos);

				// add '0' i
				if (s[s.size()-1]== '.')
					s.append("0");

			}

			return s;
		}
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
	case T_DP_DICT:
	case T_DP_LIST:
		ss << ((m_type==T_DP_DICT)?'{':'[');
		for (auto it = m_value.dpa->begin(); // std::vector<Datapoint *>*	dpa;
		     it != m_value.dpa->end();
		     ++it)
		{
			if (it != m_value.dpa->begin())
			{
				ss << ", ";
			}
			ss << ((m_type==T_DP_DICT)?(*it)->toJSONProperty():(*it)->getData().toString());
		}
		ss << ((m_type==T_DP_DICT)?'}':']');
		return ss.str();
	case T_STRING:
	default:
		ss << "\"";
		ss << *m_value.str;
		ss << "\"";
		return ss.str();
	}
}

/**
 * Delete the DatapointValue along with possibly nested Datapoint objects
 */
void DatapointValue::deleteNestedDPV()
{
	if (m_type == T_STRING)
	{
		delete m_value.str;
		m_value.str = NULL;
	}
	else if (m_type == T_FLOAT_ARRAY)
	{
		delete m_value.a;
		m_value.a = NULL;
	}
	else if (m_type == T_DP_DICT ||
		 m_type == T_DP_LIST)
	{
		if (m_value.dpa) {
			for (auto it = m_value.dpa->begin();
				 it != m_value.dpa->end();
				 ++it)
			{
				// Call DatapointValue destructor
				delete(*it);
			}

			// Remove vector pointer
			delete m_value.dpa;
			m_value.dpa = NULL;
		}
	}
}

/**
 * DatapointValue class destructor
 */
DatapointValue::~DatapointValue()
{
	// Remove memory allocated by datapoints
	// along with possibly nested Datapoint objects
	deleteNestedDPV();
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
		case T_DP_DICT:
		case T_DP_LIST:
			m_value.dpa = new std::vector<Datapoint*>();
			for (auto it = obj.m_value.dpa->begin();
				it != obj.m_value.dpa->end();
				++it)
			{
				Datapoint *d = *it;
				// Add new allocated datapoint to the vector
				// using copy constructor
				m_value.dpa->push_back(new Datapoint(*d));
			}

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
	if (m_type == T_DP_DICT || m_type == T_DP_LIST)
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
	case T_DP_DICT:
	case T_DP_LIST:
		m_value.dpa = new std::vector<Datapoint*>(*(rhs.m_value.dpa));
		break;
	default:
		m_value = rhs.m_value;
		break;
	}

	return *this;
}
