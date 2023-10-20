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
#include <exception>
#include <base64databuffer.h>
#include <base64dpimage.h>

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
		ss << "\"";
		ss << escape(*m_value.str);
		ss << "\"";
		return ss.str();
	case T_DATABUFFER:
		ss << "\"__DATABUFFER:" 
			<< ((Base64DataBuffer *)m_value.dataBuffer)->encode()
			<< "\"";
		return ss.str();
	case T_IMAGE:
		ss << "\"__DPIMAGE:" 
			<< ((Base64DPImage *)m_value.image)->encode()
			<< "\"";
		return ss.str();
	case T_2D_FLOAT_ARRAY:
		{
		ss << "[ ";
		bool first = true;
		for (auto row : *(m_value.a2d))
		{
			if (first)
				first = false;
			else
				ss << ", ";
			ss << "[";
			for (auto it = row->begin();
			     it != row->end();
			     ++it)
			{
				if (it != row->begin())
				{
					ss << ", ";
				}
				ss << *it;
			}
			ss << "]";
		}
		ss << " ]";
		return ss.str();
		}
	default:
		throw std::runtime_error("No string representation for datapoint type");
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
	else if (m_type == T_DATABUFFER)
	{
		delete m_value.dataBuffer;
		m_value.dataBuffer = NULL;
	}
	else if (m_type == T_IMAGE)
	{
		delete m_value.image;
		m_value.image = NULL;
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
	else if (m_type == T_2D_FLOAT_ARRAY)
	{
		delete m_value.a2d;
		m_value.a2d = NULL;
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
				Datapoint *dpCopy = new Datapoint(*d);
				m_value.dpa->emplace_back(dpCopy);
			}

			break;
		case T_IMAGE:
			m_value.image = new DPImage(*(obj.m_value.image));
			break;
		case T_DATABUFFER:
			m_value.dataBuffer = new DataBuffer(*(obj.m_value.dataBuffer));
			break;
		case T_2D_FLOAT_ARRAY:
			m_value.a2d = new std::vector< std::vector<double>* >;
			for (auto row : *obj.m_value.a2d)
			{
				std::vector<double> *nrow = new std::vector<double>;
				for (auto& d : *row)
				{
					nrow->push_back(d);
				}
				m_value.a2d->push_back(nrow);
			}
			m_type = T_2D_FLOAT_ARRAY;
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
	if (m_type == T_IMAGE)
	{
		delete m_value.image;
	}
	if (m_type == T_DATABUFFER)
	{
		delete m_value.dataBuffer;
	}
	if (m_type == T_2D_FLOAT_ARRAY)
	{
		delete m_value.a2d;
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
	case T_IMAGE:
		m_value.image = new DPImage(*(rhs.m_value.image));
		break;
	case T_DATABUFFER:
		m_value.dataBuffer = new DataBuffer(*(rhs.m_value.dataBuffer));
		break;
	case T_2D_FLOAT_ARRAY:
		m_value.a2d = new std::vector< std::vector<double>* >;
		for (auto row : *(rhs.m_value.a2d))
		{
			std::vector<double> *nrow = new std::vector<double>;
			for (auto& d : *row)
			{
				nrow->push_back(d);
			}
			m_value.a2d->push_back(nrow);
		}
		m_type = T_2D_FLOAT_ARRAY;
		break;
	default:
		m_value = rhs.m_value;
		break;
	}

	return *this;
}

/**
 * Escape quotes etc to allow the string to be a property value within
 * a JSON document
 *
 * @param str	The string to escape
 * @return The escaped string
 */
const std::string DatapointValue::escape(const std::string& str) const
{
std::string rval;
int bscount = 0;

	for (size_t i = 0; i < str.length(); i++)
	{
		if (str[i] == '\\')
		{
			bscount++;
		}
		else if (str[i] == '\"')
		{
			if ((bscount & 1) == 0)	// not already escaped
			{
				rval += "\\";	// Add escape of "
			}
			bscount = 0;
		}
		else
		{
			bscount = 0;
		}
		rval += str[i];
	}
	return rval;
}

/**
 * Parsing a Json string
 * 
 * @param json : string json 
 * @return vector of datapoints
*/
std::vector<Datapoint*> *Datapoint::parseJson(const std::string& json) {
	
	rapidjson::Document document;

	const auto& parseResult = document.Parse(json.c_str());
	if (parseResult.HasParseError()) {
		Logger::getLogger()->fatal("Parsing error %d (%s).", parseResult.GetParseError(), json.c_str());
		printf("Parsing error %d (%s).", parseResult.GetParseError(), json.c_str());
		return nullptr;
	}

	if (!document.IsObject()) {
		return nullptr;
	}
	return recursiveJson(document);
}

/**
 * Recursive method to convert a JSON string to a datapoint 
 * 
 * @param document : object rapidjon 
 * @return vector of datapoints
*/
std::vector<Datapoint*> *Datapoint::recursiveJson(const rapidjson::Value& document) {
	std::vector<Datapoint*>* p = new std::vector<Datapoint*>();

	for (rapidjson::Value::ConstMemberIterator itr = document.MemberBegin(); itr != document.MemberEnd(); ++itr)
	{	   
		if (itr->value.IsObject()) {
			std::vector<Datapoint*> * vec = recursiveJson(itr->value);
			DatapointValue d(vec, true);
			p->push_back(new Datapoint(itr->name.GetString(), d));
		}
		else if (itr->value.IsString()) {
			DatapointValue d(itr->value.GetString());
			p->push_back(new Datapoint(itr->name.GetString(), d));
		}
		else if (itr->value.IsDouble()) {
			DatapointValue d(itr->value.GetDouble());
			p->push_back(new Datapoint(itr->name.GetString(), d));
		}
		else if (itr->value.IsNumber() && itr->value.IsInt()) {
			DatapointValue d((long)itr->value.GetInt());
			p->push_back(new Datapoint(itr->name.GetString(), d));
		}
		else if (itr->value.IsNumber() && itr->value.IsUint()) {
			DatapointValue d((long)itr->value.GetUint());
			p->push_back(new Datapoint(itr->name.GetString(), d));
		}
		else if (itr->value.IsNumber() && itr->value.IsInt64()) {
			DatapointValue d((long)itr->value.GetInt64());
			p->push_back(new Datapoint(itr->name.GetString(), d));
		}
		else if (itr->value.IsNumber() && itr->value.IsUint64()) {
			DatapointValue d((long)itr->value.GetUint64());
			p->push_back(new Datapoint(itr->name.GetString(), d));
		}
	}

	return p;
}

