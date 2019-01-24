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

class Datapoint;
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

		DatapointValue(std::vector<Datapoint*>*& values);

		DatapointValue(const DatapointValue& obj);
		DatapointValue& operator=(const DatapointValue& rhs);
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
			if (m_type == T_DP_ARRAY)
			{
				delete m_value.dpa;
			}
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

		
		std::string	toString() const;

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
			T_FLOAT_ARRAY,
			T_DP_ARRAY
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
			std::vector<Datapoint*>*	dpa;
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

