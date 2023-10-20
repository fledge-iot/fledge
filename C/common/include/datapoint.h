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
#include <dpimage.h>
#include <databuffer.h>
#include <rapidjson/document.h>

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
		 * Construct with an Image
		 */
		DatapointValue(const DPImage& value)
		{
			m_value.image = new DPImage(value);
			m_type = T_IMAGE;
		}

		/**
		 * Construct with a DataBuffer
		 */
		DatapointValue(const DataBuffer& value)
		{
			m_value.dataBuffer = new DataBuffer(value);
			m_type = T_DATABUFFER;
		}

		/**
		 * Construct with an Image Pointer, the
		 * image becomes owned by the datapointValue
		 */
		DatapointValue(DPImage *value)
		{
			m_value.image = value;
			m_type = T_IMAGE;
		}

		/**
		 * Construct with a DataBuffer
		 */
		DatapointValue(DataBuffer *value)
		{
			m_value.dataBuffer = value;
			m_type = T_DATABUFFER;
		}

		/**
		 * Construct with a 2 dimentional  array of floating point values
		 */
		DatapointValue(const std::vector< std::vector<double> *>& values)
		{
			m_value.a2d = new std::vector< std::vector<double>* >;
			for (auto row : values)
			{
				std::vector<double> *nrow = new std::vector<double>;
				for (auto& d : *row)
				{
					nrow->push_back(d);
				}
				m_value.a2d->push_back(nrow);
			}
			m_type = T_2D_FLOAT_ARRAY;
		};

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
                 * @param value An string value to set
                 */
                void setValue(std::string value)
                {
                        if(m_value.str)
                        {
                                delete m_value.str;
                        }
                        m_value.str = new std::string(value);
                        m_type = T_STRING;
                }
	
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

		/** Set the value of a datapoint to be an image
		 * @param value The image to set in the data point
		 */
		void setValue(const DPImage& value)
		{
			m_value.image = new DPImage(value);
			m_type = T_IMAGE;
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
			T_DP_LIST,
			T_IMAGE,
			T_DATABUFFER,
			T_2D_FLOAT_ARRAY
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
				case T_IMAGE: return std::string("IMAGE");
				case T_DATABUFFER: return std::string("DATABUFFER");
				case T_2D_FLOAT_ARRAY: return std::string("2D_FLOAT_ARRAY");
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

		/**
		 * Return 2D array of float
		 */
		std::vector<std::vector<double>* >*& getDp2DArr()
		{
			return m_value.a2d;
		}

		/**
		 * Return the Image
		 */
		DPImage *getImage()
		{
			return m_value.image;
		}

		/**
		 * Return the DataBuffer
		 */
		DataBuffer *getDataBuffer()
		{
			return m_value.dataBuffer;
		}

	private:
		void deleteNestedDPV();
		const std::string	escape(const std::string& str) const;
		union data_t {
			std::string*		str;
			long			i;
			double			f;
			std::vector<double>*	a;
			std::vector<Datapoint*>
						*dpa;
			DPImage			*image;
			DataBuffer		*dataBuffer;
			std::vector< std::vector<double>* >
						*a2d;
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

		/**
		 * Parse a json string and generates 
		 * a corresponding datapoint vector  
		 */
		std::vector<Datapoint*>* parseJson(const std::string& json);
		std::vector<Datapoint*>* recursiveJson(const rapidjson::Value& document);

	private:
		std::string		m_name;
		DatapointValue		m_value;
};
#endif

