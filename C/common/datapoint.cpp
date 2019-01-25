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
			//ss << "{";   /// dict doesn't need this, list needs it, need differentiation.
			ss << ((m_type==T_DP_DICT)?(*it)->toJSONProperty():(*it)->getData().toString());
			//ss << "}";
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

