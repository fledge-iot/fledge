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
			long m_valueLong;
			std::string s;
			char tmpBuffer[100];
			snprintf(tmpBuffer, sizeof(tmpBuffer), "%.9g", m_value.f);
			s= tmpBuffer;

			m_valueLong = m_value.f;
			if (m_valueLong == m_value.f)
			{
				s.append(".0");
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
 * Delete the DatapointValue alongwith possibly nested Datapoint objects
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
	else if (m_type == T_DP_DICT || m_type == T_DP_LIST)
	{
		for (auto it = m_value.dpa->begin(); // std::vector<Datapoint *>*	dpa;
			 it != m_value.dpa->end();
			 ++it)
		{
			delete (*it);
		}
		delete m_value.dpa;
	}
}

/**
 * DatapointValue class destructor
 */
DatapointValue::~DatapointValue()
{
	if (m_type == T_STRING)
	{
		delete m_value.str;
		m_value.str = NULL;
	}
	if (m_type == T_FLOAT_ARRAY)
	{
		delete m_value.a;
		m_value.a = NULL;
	}
	// For nested DPV, d'tor is always called from holding Datapoint object's destructor
}

