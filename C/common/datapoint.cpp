/*
 * FogLAMP
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
	Logger::getLogger()->debug("%s: m_type = %d", __FUNCTION__, m_type);

	switch (m_type)
	{
	case T_INTEGER:
		ss << m_value.i;
		return ss.str();
	case T_FLOAT:
		{
		ss << std::fixed << std::setprecision(10) << m_value.f;
		std::string s = ss.str();
		s.erase(s.find_last_not_of('0') + 1, std::string::npos); // remove trailing 0's
		s = (s[s.size()-1] == '.') ? s+'0' : s; // add '0' if string ends with decimal
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
		Logger::getLogger()->debug("%s: dpv = %s", (m_type==T_DP_DICT)?"T_DP_DICT":"T_DP_LIST", ss.str().c_str());
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
		Logger::getLogger()->debug("%s:%d: deleting m_value.str, this=%p", __FUNCTION__, __LINE__, this);
		delete m_value.str;
		m_value.str = NULL;
		Logger::getLogger()->debug("%s:%d: DONE deleting m_value.str, this=%p", __FUNCTION__, __LINE__, this);
	}
	else if (m_type == T_FLOAT_ARRAY)
	{
		Logger::getLogger()->debug("%s:%d: deleting m_value.a, this=%p", __FUNCTION__, __LINE__, this);
		delete m_value.a;
		m_value.a = NULL;
		Logger::getLogger()->debug("%s:%d: DONE deleting m_value.a, this=%p", __FUNCTION__, __LINE__, this);
	}
	else if (m_type == T_DP_DICT || m_type == T_DP_LIST)
	{
		Logger::getLogger()->debug("%s:%d: deleting m_value.dpa, this=%p", __FUNCTION__, __LINE__, this);
		for (auto it = m_value.dpa->begin(); // std::vector<Datapoint *>*	dpa;
			 it != m_value.dpa->end();
			 ++it)
		{
			delete (*it);
		}
		delete m_value.dpa;
		Logger::getLogger()->debug("%s:%d: DONE deleting m_value.dpa, this=%p", __FUNCTION__, __LINE__, this);
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

