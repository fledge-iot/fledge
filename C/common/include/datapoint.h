#ifndef _DATAPOINT_H
#define _DATAPOINT_H
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
				break;
			default:
				m_value = obj.m_value;
				break;
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
		 * Assignment Operator
		 */
		DatapointValue& operator=(const DatapointValue& rhs)
		{
			if (m_type == T_STRING)
			{
				// Remove previous value
				delete m_value.str;
			}

			m_type = rhs.m_type;

			switch (m_type)
			{
			case T_STRING:
				m_value.str = new std::string(*(rhs.m_value.str));
				break;
			default:
				m_value = rhs.m_value;
				break;
			}

			return *this;
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
				ss << "\"";
				ss << *m_value.str;
				ss << "\"";
				return ss.str();
			}
		};

		typedef enum DatapointTag { T_STRING, T_INTEGER, T_FLOAT } dataTagType;

		/**
		 * Return the Tag type
		 */
		dataTagType getType() const
		{
			return m_type;
		}
	private:
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
			std::string rval = "\"" + m_name + "\" : ";
			rval += m_value.toString();

			return rval;
		}

		// Return get Datapoint name
		const std::string getName() const
		{
			return m_name;
		}

		// Return Datapoint value
		const DatapointValue getData() const
		{
			return m_value;
		}
	private:
		const std::string	m_name;
		const DatapointValue	m_value;
};
#endif

