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

/**
 * Class to hold an actual reading value.
 * The class is simply a tagged union that also contains
 * methods to return the value as a string for encoding
 * in a JSON document.
 */
class DatapointValue {
	public:
		/**
		 * Construct with a string
		 */
		DatapointValue(const std::string& value)
		{
			m_value.str = new std::string(value);
			m_type = T_STRING;
		};
		/**
 		 * Construct with an integer value
		 */
		DatapointValue(const int value)
		{
			m_value.i = value;
			m_type = T_INTEGER;
		};
		/**
		 * Construct with a floating point value
		 */
		DatapointValue(const double value)
		{
			m_value.f = value;
			m_type = T_FLOAT;
		};
		/**
		 * Copy constructor
		 */
		DatapointValue(const DatapointValue& obj)
		{
			m_type = obj.m_type;
			switch (m_type)
			{
			case T_STRING:
				m_value.str = new std::string(*(obj.m_value.str));
			default:
				m_value = obj.m_value;
			}
		}
		/**
		 * Destructor
		 */
		~DatapointValue()
		{
			if (m_type == T_STRING)
			{
				delete m_value.str;
			}
		};
		/**
		 * Return the value as a string
		 */
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

/**
 * Name and value pair used to represent a data value
 * within an asset reading.
 */
class Datapoint {
	public:
		/**
		 * Construct with a data point value
		 */
		Datapoint(const std::string& name, DatapointValue& value) : m_name(name), m_value(value)
		{
		}
		/**
		 * Return asset reading data point as a JSON
		 * property that can be included within a JSON
		 * document.
		 */
		std::string	toJSONProperty()
		{
			std::string rval = "\"" + m_name;
			rval += "\" : \"";
			rval += m_value.toString();
			rval += "\"";
			return rval;
		}
	private:
		const std::string	m_name;
		const DatapointValue	m_value;
};
#endif

