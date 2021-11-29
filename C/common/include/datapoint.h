#ifndef _DATAPOINT_H
#define _DATAPOINT_H
/*
 * Fledge
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
#include <logger.h>

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

		/**
		 * Construct with an array of Datapoints
		 */
		DatapointValue(std::vector<Datapoint*>*& values, bool isDict)
		{
			m_value.dpa = values;
			m_type = isDict? T_DP_DICT : T_DP_LIST;
		}

		/**
		 * Copy constructor
		 */
		DatapointValue(const DatapointValue& obj);

		/**
		 * Assignment Operator
		 */
		DatapointValue& operator=(const DatapointValue& rhs);

		/**
		 * Destructor
		 */
		~DatapointValue();

		
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
		std::string	toString() const;

		/**
		 * Return string value without trailing/leading quotes
		 */
		std::string	toStringValue() const { return *m_value.str; };

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
			T_DP_DICT,
			T_DP_LIST
		} dataTagType;

		/**
		 * Return the Tag type
		 */
		dataTagType getType() const
		{
			return m_type;
		}

		std::string getTypeStr() const
		{
			switch(m_type)
			{
				case T_STRING: return std::string("STRING");
				case T_INTEGER: return std::string("INTEGER");
				case T_FLOAT: return std::string("FLOAT");
				case T_FLOAT_ARRAY: return std::string("FLOAT_ARRAY");
				case T_DP_DICT: return std::string("DP_DICT");
				case T_DP_LIST: return std::string("DP_LIST");
				default: return std::string("INVALID");
			}
		}

		/**
		 * Return array of datapoints
		 */
		std::vector<Datapoint*>*& getDpVec()
		{
			return m_value.dpa;
		}

		/**
		 * Return array of float
		 */
		std::vector<double>*& getDpArr()
		{
			return m_value.a;
		}

	private:
		void deleteNestedDPV();
		const std::string	escape(const std::string& str) const;
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

		~Datapoint()
		{
		}
		/**
		 * Return asset reading data point as a JSON
		 * property that can be included within a JSON
		 * document.
		 */
		std::string	toJSONProperty()
		{
			std::string rval = "\"" + m_name + "\":";
			rval += m_value.toString();

			return rval;
		}

		/**
		 * Return the Datapoint name
		 */
		const std::string getName() const
		{
			return m_name;
		}

		/**
		 * Rename the datapoint
		 */
		void setName(std::string name)
		{
			m_name = name;
		}

		/**
		 * Return Datapoint value
		 */
		const DatapointValue getData() const
		{
			return m_value;
		}

		/**
		 * Return reference to Datapoint value
		 */
		DatapointValue& getData()
		{
			return m_value;
		}
	private:
		std::string		m_name;
		DatapointValue		m_value;
};
#endif

