#ifndef _DATAPOINT_H
#define _DATAPOINT_H
/*
 * FogLAMP
 *
 * Copyright (c) 2018 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <string>
#include <sstream>

class DatapointValue {
	public:
		DatapointValue(const std::string& value)
		{
			m_value.str = new std::string(value);
			m_type = T_STRING;
		};
		DatapointValue(const int value)
		{
			m_value.i = value;
			m_type = T_INTEGER;
		};
		DatapointValue(const double value)
		{
			m_value.f = value;
			m_type = T_FLOAT;
		};
		~DatapointValue()
		{
			if (m_type == T_STRING)
			{
				delete m_value.str;
			}
		};
		std::string	toString() const
		{
			std::ostringstream ss;
			switch (m_type)
			{
			case T_INTEGER:
				ss << m_value.i;
				return ss.str();
			case T_FLOAT:
				ss << m_value.f;
				return ss.str();
			case T_STRING:
			default:
				return *m_value.str;
			}
		};
	private:
		enum DatapointTag { T_STRING, T_INTEGER, T_FLOAT };
		union data_t {
			std::string	*str;
			int		i;
			double		f;
			} m_value;
		DatapointTag	m_type;
};

class Datapoint {
	public:
		Datapoint(const std::string& name, DatapointValue& value) : m_name(name), m_value(value)
		{
		}
		std::string	toJSONProperty()
		{
			std::string rval = "\"" + m_name;
			rval += "\" ; \"";
			rval += m_value.toString();
			rval += "\"";
			return rval;
		}
	private:
		const std::string	m_name;
		const DatapointValue	m_value;
};
#endif

