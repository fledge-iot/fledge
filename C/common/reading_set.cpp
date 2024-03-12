/*
 * Fledge storage service client
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch, Massimiliano Pinto
 */
#include <reading_set.h>
#include <string>
#include <rapidjson/document.h>
#include <sstream>
#include <iostream>
#include <time.h>
#include <stdlib.h>
#include <logger.h>
#include <base64databuffer.h>
#include <base64dpimage.h>

#include <boost/algorithm/string/replace.hpp>

#define ASSET_NAME_INVALID_READING "error_invalid_reading"

static const char* kTypeNames[] =
    { "Null", "False", "True", "Object", "Array", "String", "Number" };

using namespace std;
using namespace rapidjson;

// List of characters to be escaped in JSON
const vector<string> JSON_characters_to_be_escaped = {
	"\\",
	"\""
};

/**
 * Construct an empty reading set
 */
ReadingSet::ReadingSet() : m_count(0), m_last_id(0)
{
}

/**
 * Construct a reading set from a vector<Reading *> pointer
 * NOTE: readings are copied into m_readings
 *
 * @param readings	The  vector<Reading *> pointer
 *			of readings to be copied
 *			into m_readings vector
 */
ReadingSet::ReadingSet(const vector<Reading *>* readings) : m_last_id(0)
{
	m_count = readings->size();
	for (auto it = readings->begin(); it != readings->end(); ++it)
	{
		if ((*it)->hasId() && (*it)->getId() > m_last_id)
			m_last_id = (*it)->getId();
		m_readings.push_back(*it);
	}
}

/**
 * Construct a reading set from a JSON document returned from
 * the Fledge storage service query or notification. The JSON
 * is parsed using the in-situ RapidJSON parser in order to
 * reduce overhead on what is most likely a large JSON document.
 *
 * WARNING: Although the string passed in is defiend as const
 * this call is destructive to this string and the conntents
 * of the string should not be used after making this call.
 *
 * @param json	The JSON document (as string) with readings data
 */
ReadingSet::ReadingSet(const std::string& json) : m_last_id(0)
{
	unsigned long rows = 0;
	Document doc;
	doc.ParseInsitu((char *)json.c_str());	// Cast away const in order to use in-situ
	if (doc.HasParseError())
	{
		throw new ReadingSetException("Unable to parse results json document");
	}
	// Check we have "count" and "rows"
	bool docHasRows =  doc.HasMember("rows"); // Query
	bool docHasReadings =  doc.HasMember("readings"); // Notification

	// Check we have "rows" or "readings"
	if (!docHasRows && !docHasReadings)
	{
		throw new ReadingSetException("Missing readings or rows array");
	}

	// Check we have "count" and "rows"
	if (doc.HasMember("count") && docHasRows)
	{
		m_count = doc["count"].GetUint();
		// No readings
		if (!m_count)
		{
			m_last_id = 0;
			return;
		}
	}
	else
	{
		// These fields might be updated later
		m_count = 0;
		m_last_id = 0;
	}

	// Get "rows" or "readings" data
	const Value& readings = docHasRows ? doc["rows"] : doc["readings"];
	if (readings.IsArray())
	{
		unsigned long id = 0;
		// Process every rows and create the result set
		for (auto& reading : readings.GetArray())
		{
			if (!reading.IsObject())
			{
				throw new ReadingSetException("Expected reading to be an object");
			}
			JSONReading *value = new JSONReading(reading);
			m_readings.push_back(value);

			// Get the Reading Id
			id = value->getId();

			// We don't have count informations with "readings"
			if (docHasReadings)
			{
				rows++;
			}

		}
		// Set the last id
		m_last_id = id;

		// Set count informations with "readings"
		if (docHasReadings)
		{
			m_count = rows;
		}
	}
	else
	{
		throw new ReadingSetException("Expected array of rows in result set");
	}
}

/**
 * Destructor for a result set
 */
ReadingSet::~ReadingSet()
{
	/* Delete the readings */
	for (auto it = m_readings.cbegin(); it != m_readings.cend(); it++)
	{
		delete *it;
	}
}

/**
 * Append the readings in a second reading set to this reading set.
 * The readings are removed from the original reading set
 *
 * @param readings	A ReadingSet to append to the current ReadingSet
 */
void
ReadingSet::append(ReadingSet *readings)
{
	vector<Reading *> *vec = readings->getAllReadingsPtr();
	append(*vec);
	readings->clear();
}

/**
 * Append the readings in a second reading set to this reading set.
 * The readings are removed from the original reading set
 *
 * @param readings	A ReadingSet to append to the current ReadingSet
 */
void
ReadingSet::append(ReadingSet& readings)
{
	vector<Reading *> *vec = readings.getAllReadingsPtr();
	append(*vec);
	readings.clear();
}

/**
 * Append a set of readings to this reading set. The
 * readings are not copied, but rather moved from the
 * vector, with the resulting vector havign the values
 * removed on return.
 *
 * It is assumed the readings in the vector have been
 * created with the new operator.
 *
 * @param readings	A vector of Reading pointers to append to the ReadingSet
 */
void
ReadingSet::append(vector<Reading *>& readings)
{
	for (auto it = readings.cbegin(); it != readings.cend(); it++)
	{
		if ((*it)->getId() > m_last_id)
			m_last_id = (*it)->getId();
		m_readings.push_back(*it);
		m_count++;
	}
	readings.clear();
}

/**
* Deep copy a set of readings to this reading set.
*/
bool
ReadingSet::copy(const ReadingSet& src)
{
	vector<Reading *> readings;
	bool copyResult = true;
	try
	{
		// Iterate over all the readings in ReadingSet
		for (auto const &reading : src.getAllReadings())
		{
			std::string assetName = reading->getAssetName();
			std::vector<Datapoint *> dataPoints;
			try
			{
				// Iterate over all the datapoints associated with one reading
				for (auto const &dp : reading->getReadingData())
				{
					std::string dataPointName  = dp->getName();
					DatapointValue dv = dp->getData();
					dataPoints.emplace_back(new Datapoint(dataPointName, dv));
					
				}
			}
			// Catch exception while copying datapoints
			catch(std::bad_alloc& ex)
			{
				Logger::getLogger()->error("Insufficient memory, failed while copying dataPoints from ReadingSet, %s ", ex.what());
				copyResult = false;
				for (auto const &dp : dataPoints)
				{
					delete dp;
				}
				dataPoints.clear();
				throw;
			}
			catch (std::exception& ex)
			{
				Logger::getLogger()->error("Unknown exception, failed while copying datapoint from ReadingSet, %s ", ex.what());
				copyResult = false;
				for (auto const &dp : dataPoints)
				{
					delete dp;
				}
				dataPoints.clear();
				throw;
			}
			
			Reading *in = new Reading(assetName, dataPoints);
			readings.emplace_back(in);
	   }
   }
   // Catch exception while copying readings
   catch (std::bad_alloc& ex)
   {
		Logger::getLogger()->error("Insufficient memory, failed while copying %d reading from ReadingSet, %s ",readings.size()+1, ex.what());
		copyResult = false;
		for (auto const &r : readings)
		{
			delete r;
		}
		readings.clear();
   }
   catch (std::exception& ex)
   {
		Logger::getLogger()->error("Unknown exception, failed while copying %d reading from ReadingSet, %s ",readings.size()+1, ex.what());
		copyResult = false;
		for (auto const &r : readings)
		{
			delete r;
		}
		readings.clear();
   }

   //Append if All elements have been copied successfully
   if (copyResult)
   {
	   append(readings);
   }

   return copyResult;
}

/**
 * Remove all readings from the reading set and delete the memory
 * After this call the reading set exists but contains no readings.
 */
void
ReadingSet::removeAll()
{
	for (auto it = m_readings.cbegin(); it != m_readings.cend(); it++)
	{
		delete *it;
	}
	m_readings.clear();
	m_count = 0;
	m_last_id = 0;
}

/**
 * Remove the readings from the vector without deleting them
 */
void
ReadingSet::clear()
{
	m_readings.clear();
	m_count = 0;
	m_last_id = 0;
}

/**
 * Remove readings from the vector and return a reference to new vector
 * containing readings*
*/
std::vector<Reading*>* ReadingSet::moveAllReadings()
{
	std::vector<Reading*>* transferredPtr = new std::vector<Reading*>(std::move(m_readings));
	m_count = 0;
	m_last_id = 0;
	m_readings.clear();

	return transferredPtr;
}

/**
 * Remove reading from vector based on index and return its pointer
*/
Reading* ReadingSet::removeReading(unsigned long id)
{
	if (id >= m_readings.size())
	{
		return nullptr;
	}

	Reading* reading = m_readings[id];
	m_readings.erase(m_readings.begin() + id);
	m_count--;

	return reading;
}

/**
 * Return the ID of the nth reading in the reading set
 *
 * @param pos	The position of the reading to return the ID for
 */
unsigned long ReadingSet::getReadingId(uint32_t pos)
{
	if (pos < m_readings.size())
	{
		Reading *reading = m_readings[pos];
		return reading->getId();
	}
	return m_last_id;
}

/**
 * Construct a reading from a JSON document
 *
 * The data can be in the "value" property as single numeric value
 * or in the JSON "reading" with different values and types
 *
 * @param json	The JSON document that contains the reading
 */
JSONReading::JSONReading(const Value& json)
{
	if (json.HasMember("id"))
	{
		m_id = json["id"].GetUint64();
		m_has_id = true;
	}
	else
	{
		m_has_id = false;
	}
	if (json.HasMember("asset_code"))
	{
		m_asset = json["asset_code"].GetString();
	}
	else
	{
		string errMsg = "Malformed JSON reading, missing asset_code '";
		errMsg.append("value");
		errMsg += "'";
		throw new ReadingSetException(errMsg.c_str());
	}
	if (json.HasMember("user_ts"))
	{
		stringToTimestamp(json["user_ts"].GetString(), &m_userTimestamp);
	}
	else
	{
		string errMsg = "Malformed JSON reading, missing user timestamp '";
		errMsg.append("value");
		errMsg += "'";
		throw new ReadingSetException(errMsg.c_str());
	}
	if (json.HasMember("ts"))
	{
		stringToTimestamp(json["ts"].GetString(), &m_timestamp);
	}
	else
	{
		m_timestamp = m_userTimestamp;
	}

	// We have a single value here which is a number
	if (json.HasMember("value") && json["value"].IsNumber())
	{
		const Value &m = json["value"];
		
		if (m.IsInt() ||
		    m.IsUint() ||
		    m.IsInt64() ||
		    m.IsUint64())
		{
			DatapointValue* value;
			if (m.IsInt() ||
			    m.IsUint() )
			{
				value = new DatapointValue((long) m.GetInt());
			}
			else
			{
				value = new DatapointValue((long) m.GetInt64());
			}
			this->addDatapoint(new Datapoint("value",*value));
			delete value;

		}
		else if (m.IsDouble())
		{
			DatapointValue value(m.GetDouble());
			this->addDatapoint(new Datapoint("value",
							 value));
		}
		else
		{
			string errMsg = "Cannot parse the numeric type";
			errMsg += " of reading element '";
			errMsg.append("value");
			errMsg += "'";

			throw new ReadingSetException(errMsg.c_str());
		}
	}
	else if (json.HasMember("reading"))
	{
		if (json["reading"].IsObject())
		{
			// Add 'reading' values
			for (auto &m : json["reading"].GetObject())
			{
				addDatapoint(datapoint(m.name.GetString(), m.value));
			}
		}
		else
		{
			// The reading should be an object at this stage, it is and invalid one if not
			// the asset name ASSET_NAME_INVALID_READING will be created in the PI-Server containing the
			// invalid asset_name/values.
			if (json["reading"].IsString())
			{
				string tmp_reading1 = json["reading"].GetString();

				// Escape specific character for to be properly manage as JSON
				for (const string &item : JSON_characters_to_be_escaped)
				{

					escapeCharacter(tmp_reading1, item);
				}

				Logger::getLogger()->error(
					"Invalid reading: Asset name |%s| reading value |%s| converted value |%s|",
					m_asset.c_str(),
					json["reading"].GetString(),
					tmp_reading1.c_str());

				DatapointValue value(tmp_reading1);
				this->addDatapoint(new Datapoint(m_asset, value));

			} else if (json["reading"].IsInt() ||
				   json["reading"].IsUint() ||
				   json["reading"].IsInt64() ||
				   json["reading"].IsUint64()) {

				DatapointValue *value;

				if (json["reading"].IsInt() ||
				    json["reading"].IsUint()) {
					value = new DatapointValue((long) json["reading"].GetInt());
				} else {
					value = new DatapointValue((long) json["reading"].GetInt64());
				}
				this->addDatapoint(new Datapoint(m_asset, *value));
				delete value;

			} else if (json["reading"].IsDouble())
			{
				DatapointValue value(json["reading"].GetDouble());
				this->addDatapoint(new Datapoint(m_asset, value));

			}

			m_asset = string(ASSET_NAME_INVALID_READING) + string("_") + m_asset.c_str();
		}
	}
	else
	{
		Logger::getLogger()->error("Missing reading property for JSON reading, %s", m_asset.c_str());
	}
}

/**
 * Create a Datapoint from a JSON item in a reading
 *
 * @param item	The JSON object forthe data point
 * @return Datapoint* The new data point
 */
Datapoint *JSONReading::datapoint(const string& name, const Value& item)
{
Datapoint *rval = NULL;

	switch (item.GetType())
	{
		// String
		case (kStringType):
		{
			string str = item.GetString();
			if (str[0] == '_' && str[1] == '_')
			{
				// special encoded type
				size_t pos = str.find_first_of(':');
				if (str.compare(2, 10, "DATABUFFER") == 0)
				{
					try {
						DataBuffer *databuffer = new Base64DataBuffer(str.substr(pos + 1));
						DatapointValue value(databuffer);
						rval = new Datapoint(name, value);
					} catch (exception& e) {
						Logger::getLogger()->error("Unable to create datapoint %s as the base 64 encoded data is incorrect, %s",
								name.c_str(), e.what());
					}
				}
				else if (str.compare(2, 7, "DPIMAGE") == 0)
				{
					try {
						DPImage *image = new Base64DPImage(str.substr(pos + 1));
						DatapointValue value(image);
						rval = new Datapoint(name, value);
					} catch (exception& e) {
						Logger::getLogger()->error("Unable to create datapoint %s as the base 64 encoded data is incorrect, %s",
								name.c_str(), e.what());
					}
				}

			}
			else
			{
				DatapointValue value(item.GetString());
				rval = new Datapoint(name, value);
			}
			break;
		}

		// Number
		case (kNumberType):
		{
			if (item.IsInt())
			{
				DatapointValue value((long)item.GetInt());
				rval = new Datapoint(name, value);
				break;
			}
			else if (item.IsUint())
			{
				DatapointValue value((long)item.GetUint());
				rval = new Datapoint(name, value);
				break;
			}
			else if (item.IsInt64())
			{
				DatapointValue value((long)item.GetInt64());
				rval = new Datapoint(name, value);
				break;
			}
			else if (item.IsUint64())
			{
				DatapointValue value((long)item.GetUint64());
				rval = new Datapoint(name, value);
				break;
			}
			else if (item.IsDouble())
			{
				DatapointValue value(item.GetDouble());
				rval = new Datapoint(name, value);
				break;
			}
			else
			{
				string errMsg = "Cannot parse the numeric type";
				errMsg += " of reading element '";
				errMsg.append(name);
				errMsg += "'";

				throw new ReadingSetException(errMsg.c_str());
				break;
			}
		}

		// Arrays
		case kArrayType:
		{
			vector<double> arrayValues;
			for (auto& v : item.GetArray())
			{
				if (v.IsDouble())
				{
					arrayValues.push_back(v.GetDouble());
				}
				else if (v.IsInt() || v.IsUint())
				{
					double i = (double)v.GetInt();
					arrayValues.push_back(i);
				}
				else if (v.IsInt64() || v.IsUint64())
				{
					double i = (double)v.GetInt64();
					arrayValues.push_back(i);
				}
			}
			DatapointValue value(arrayValues);
			rval = new Datapoint(name, value);
			break;
			    
		}
	
		// Nested object
		case kObjectType:
		{
			vector<Datapoint *> *obj = new vector<Datapoint *>;
			for (auto &mo : item.GetObject())
			{
				Datapoint *dp = datapoint(mo.name.GetString(), mo.value);
				if (dp)
				{
					obj->push_back(dp);
				}
			}
			DatapointValue value(obj, true);
			rval = new Datapoint(name, value);
			break;
		}

		case kTrueType:
		{
			DatapointValue value("true");
			rval = new Datapoint(name, value);
			break;
		}
		case kFalseType:
		{
			DatapointValue value("false");
			rval = new Datapoint(name, value);
			break;
		}

		default:
		{
			char errMsg[80];
		       	snprintf(errMsg, sizeof(errMsg), "Unhandled type for %s in JSON payload %d", name.c_str(), item.GetType());
			throw new ReadingSetException(errMsg);
		}
	}
	return rval;
}

/**
 * Escapes a character in a string to be properly handled as JSON
 *
 */
void JSONReading::escapeCharacter(string& stringToEvaluate, string pattern)
{
	string escaped = "\\" + pattern;

	boost::replace_all(stringToEvaluate, pattern, escaped);
}
