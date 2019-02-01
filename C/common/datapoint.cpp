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
 */
std::string	DatapointValue::toString() const
{
	std::ostringstream ss;
	Logger::getLogger()->info("%s: m_type = %d", __FUNCTION__, m_type);

	switch (m_type)
	{
	case T_INTEGER:
		ss << m_value.i;
		return ss.str();
	case T_FLOAT:
		ss.setf(std::ios::showpoint);
		ss << std::setprecision(DBL_DIG);
		ss << m_value.f;
		Logger::getLogger()->info("DatapointValue::toString(): T_FLOAT: value=%f, ss=%s", m_value.f, ss.str().c_str());
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
		Logger::getLogger()->info("%s: dpv = %s", (m_type==T_DP_DICT)?"T_DP_DICT":"T_DP_LIST", ss.str().c_str());
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
	//Logger::getLogger()->info("%s:%d: m_type = %s", __FUNCTION__, __LINE__, getTypeStr().c_str());
	if (m_type == T_STRING)
	{
		Logger::getLogger()->info("%s:%d: deleting m_value.str, this=%p", __FUNCTION__, __LINE__, this);
		delete m_value.str;
		m_value.str = NULL;
		Logger::getLogger()->info("%s:%d: DONE deleting m_value.str, this=%p", __FUNCTION__, __LINE__, this);
	}
	else if (m_type == T_FLOAT_ARRAY)
	{
		Logger::getLogger()->info("%s:%d: deleting m_value.a, this=%p", __FUNCTION__, __LINE__, this);
		delete m_value.a;
		m_value.a = NULL;
		Logger::getLogger()->info("%s:%d: DONE deleting m_value.a, this=%p", __FUNCTION__, __LINE__, this);
	}
	else if (m_type == T_DP_DICT || m_type == T_DP_LIST)
	{
		Logger::getLogger()->info("%s:%d: deleting m_value.dpa, this=%p", __FUNCTION__, __LINE__, this);
		for (auto it = m_value.dpa->begin(); // std::vector<Datapoint *>*	dpa;
			 it != m_value.dpa->end();
			 ++it)
		{
#if 0
			// '*it' is of 'Datapoint*' type
			DatapointValue &dpv = (*it)->getData();
			Logger::getLogger()->info("%s:%d: deleting dpa element: dpv.getTypeStr()=%s", __FUNCTION__, __LINE__, dpv.getTypeStr().c_str());
			// if this dpv is of dict/list type, need to free up nested DPVs also
			if (dpv.getType() == T_DP_DICT || dpv.getType() == T_DP_LIST)
			{
				Logger::getLogger()->info("%s:%d: deleting nested dpv", __FUNCTION__, __LINE__);
				for (auto it2 = dpv.getDpVec()->begin(); // std::vector<Datapoint *>*	dpa;
					 it2 != dpv.getDpVec()->end();
					 ++it2)
				{
					// '*it2' is of 'Datapoint*' type
					delete (*it2);
				}
			}
			else
			{
				Logger::getLogger()->info("%s:%d: deleting non-nested dpv", __FUNCTION__, __LINE__);
				dpv.deleteNestedDPV();
			}
			Logger::getLogger()->info("%s:%d: DONE deleting dpa element: dpv.getTypeStr()=%s", __FUNCTION__, __LINE__, dpv.getTypeStr().c_str());
#endif
			delete (*it);
		}
		delete m_value.dpa;
		Logger::getLogger()->info("%s:%d: DONE deleting m_value.dpa, this=%p", __FUNCTION__, __LINE__, this);
	}
}

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
	//DPV d'tor is always called from holding Datapoint object's destructor
	//if (m_type == T_STRING || m_type == T_FLOAT_ARRAY)
	//		deleteNestedDPV();
}

