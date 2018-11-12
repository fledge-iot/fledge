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
#include <iomanip>
#include <cfloat>
#include <vector>

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
		DatapointValue(const long value)
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
		 * Construct with an array of floating point values
		 */
		DatapointValue(const std::vector<double>& values)
		{
			m_value.a = new std::vector<double>(values);
			m_type = T_FLOAT_ARRAY;
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
			case T_FLOAT_ARRAY:
				m_value.a = new std::vector<double>(*(obj.m_value.a));
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
			if (m_type == T_FLOAT_ARRAY)
			{
				delete m_value.a;
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
			if (m_type == T_FLOAT_ARRAY)
			{
				// Remove previous value
				delete m_value.a;
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
			default:
				m_value = rhs.m_value;
				break;
			}

			return *this;
		};

		/**
		 * Set the value of a datapoint, this may
		 * also cause the type to be changed.
		 * @param value	An integer value to set
		 */
		void setValue(long value)
		{
			m_value.i = value;
			m_type = T_INTEGER;
		}

		/**
		 * Set the value of a datapoint, this may
		 * also cause the type to be changed.
		 * @param value	A floating point value to set
		 */
		void setValue(double value)
		{
			m_value.f = value;
			m_type = T_FLOAT;
		}

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
			case T_STRING:
			default:
				ss << "\"";
				ss << *m_value.str;
				ss << "\"";
				return ss.str();
			}
		};

		/**
		 * Return long value
		 */
		long toInt() const { return m_value.i; };
		/**
		 * Return double value
		 */
		double toDouble() const { return m_value.f; };

		// Supported Data Tag Types
		typedef enum DatapointTag
		{
			T_STRING,
			T_INTEGER,
			T_FLOAT,
			T_FLOAT_ARRAY
		} dataTagType;

		/**
		 * Return the Tag type
		 */
		dataTagType getType() const
		{
			return m_type;
		}
	private:
		union data_t {
			std::string*		str;
			long			i;
			double			f;
			std::vector<double>*	a;
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
		// Return reference to Datapoint value
		DatapointValue& getData()
		{
			return m_value;
		}
	private:
		const std::string	m_name;
		DatapointValue		m_value;
};
#endif

