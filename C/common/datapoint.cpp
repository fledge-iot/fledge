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

DatapointValue* createDictDPV(const DatapointValue &dpv_orig);
DatapointValue* createListDPV(const DatapointValue &dpv_orig);

DatapointValue* createBasicDPV(const DatapointValue &dpv)
{
	DatapointValue::dataTagType t = dpv.getType();
	DatapointValue* dpv2 = NULL;
	switch (t)
	{
		case DatapointValue::T_STRING:
			// const std::string *s = new std::string(dpv.toStringValue());
			dpv2 = new DatapointValue(dpv.toStringValue());
			break;
		case DatapointValue::T_INTEGER:
			dpv2 = new DatapointValue(dpv.toInt());
			break;
		case DatapointValue::T_FLOAT:
			dpv2 = new DatapointValue(dpv.toDouble());
			break;
		case DatapointValue::T_FLOAT_ARRAY:
			//std::vector<double> *arr = new std::vector<double>(dpv.getDpArr());
			dpv2 = new DatapointValue(*(dpv.getDpArr()));
			Logger::getLogger()->info("T_FLOAT_ARRAY: old vector @ %p, new vector @ %p", dpv.getDpArr(), dpv2->getDpArr());
			break;
		default:
			Logger::getLogger()->info("%s unhandled case", __FUNCTION__);
	}
	return dpv2;
}


DatapointValue* createDictDPV(const DatapointValue &dpv_orig)
{
	const std::vector<Datapoint*> *data = dpv_orig.getDpVec();

	if(!data)
	{
		Logger::getLogger()->info("dict has NULL DP vector");
		return NULL;
	}
	
	std::vector<Datapoint*> *dpVec = new std::vector<Datapoint*>();  // these DPs go inside dict DPV
	Logger::getLogger()->info("T_DP_DICT: old vector @ %p, new vector @ %p", *data, *dpVec);
	
	for(auto &dp: *data)
	{
		DatapointValue* dpv = NULL;
		DatapointValue::dataTagType t = dp->getData().getType();
		switch (t)
		{
			case DatapointValue::T_STRING:
			case DatapointValue::T_INTEGER:
			case DatapointValue::T_FLOAT:
			case DatapointValue::T_FLOAT_ARRAY:
				dpv = createBasicDPV(dp->getData());
				break;

			case DatapointValue::T_DP_DICT:
				dpv = createDictDPV(dp->getData());
				break;

			case DatapointValue::T_DP_LIST:
				dpv = createListDPV(dp->getData());
				break;
			default:
				Logger::getLogger()->info("%s unhandled case", __FUNCTION__);
		}

		if (dpv)
		{
			Datapoint *dp2 = new Datapoint(dp->getName(), *dpv);
			Logger::getLogger()->info("T_DP_DICT: DPV type=%s, old DP @ %p, new DP @ %p", dpv->getTypeStr(), *dp, *dp2);
			dpVec->emplace_back(dp2);
			delete dpv;
		}
	}
	if (dpVec->size() > 0)
	{
		DatapointValue *dpv = new DatapointValue(dpVec, true);
		Logger::getLogger()->info("T_DP_DICT: old dict DPV @ 'UNKNOWN', new dict DPV @ %p", *dpv);
		return dpv;
	}
	else
	{
		delete dpVec;
		return NULL;
	}
}

DatapointValue* createListDPV(const DatapointValue &dpv_orig)
{
	const std::vector<Datapoint*> *data = dpv_orig.getDpVec();

	if(!data)
	{
		Logger::getLogger()->info("list has NULL DP vector");
		return NULL;
	}
	
	std::vector<Datapoint*> *dpVec = new std::vector<Datapoint*>();  // these DPs go inside list DPV
	Logger::getLogger()->info("T_DP_LIST: old vector @ %p, new vector @ %p", *data, *dpVec);
	int i=0;

	for(auto &dp: *data)
	{
		DatapointValue* dpv = NULL;
		DatapointValue::dataTagType t = dp->getData().getType();
		switch (t)
		{
			case DatapointValue::T_STRING:
			case DatapointValue::T_INTEGER:
			case DatapointValue::T_FLOAT:
			case DatapointValue::T_FLOAT_ARRAY:
				dpv = createBasicDPV(dp->getData());
				break;

			case DatapointValue::T_DP_DICT:
				dpv = createDictDPV(dp->getData());
				break;

			case DatapointValue::T_DP_LIST:
				dpv = createListDPV(dp->getData());
				break;
			default:
				Logger::getLogger()->info("%s unhandled case", __FUNCTION__);
		}

		if (dpv)
		{
			Datapoint *dp2 = new Datapoint(std::string("unnamed_list_elem#") + std::to_string(i), *dpv);
			Logger::getLogger()->info("T_DP_LIST: DPV type=%s, old DP @ %p, new DP @ %p", dpv->getTypeStr(), *dp, *dp2);
			dpVec->emplace_back(dp2);
			i++;
			delete dpv;
		}
	}
	if (dpVec->size() > 0)
	{
		DatapointValue *dpv = new DatapointValue(dpVec, false);
		Logger::getLogger()->info("T_DP_LIST: old list DPV @ 'UNKNOWN', new list DPV @ %p", *dpv);
		return dpv;
	}
	else
	{
		delete dpVec;
		return NULL;
	}
}

/**
 * Copy constructor
 */
DatapointValue::DatapointValue(const DatapointValue& obj)
{
	m_type = obj.getType();
	
	DatapointValue* dpv = NULL;
	switch (m_type)
	{
		case T_STRING:
		case T_INTEGER:
		case T_FLOAT:
		case T_FLOAT_ARRAY:
			dpv = createBasicDPV(obj);
			break;

		case T_DP_DICT:
			dpv = createDictDPV(obj);
			break;
			
		case T_DP_LIST:
			dpv = createListDPV(obj);
			break;
		default:
			Logger::getLogger()->info("%s unhandled case", __FUNCTION__);
	}
	m_value = dpv->m_value;
}


/**
 * Assignment Operator
 */
DatapointValue& DatapointValue::operator=(const DatapointValue& obj)
{
	m_type = obj.getType();
	
	DatapointValue* dpv = NULL;
	switch (m_type)
	{
		case T_STRING:
		case T_INTEGER:
		case T_FLOAT:
		case T_FLOAT_ARRAY:
			dpv = createBasicDPV(obj);
			break;

		case T_DP_DICT:
			dpv = createDictDPV(obj);
			break;
			
		case T_DP_LIST:
			dpv = createListDPV(obj);
			break;
		default:
			Logger::getLogger()->info("%s unhandled case", __FUNCTION__);
	}
	m_value = dpv->m_value;
	return *this;
}

Datapoint::Datapoint(const Datapoint& obj)
{
	m_name = obj.getName();
	m_value = obj.getData();
}

