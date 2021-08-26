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
ReadingSet::ReadingSet(vector<Reading *>* readings) : m_last_id(0)
{
	m_count = readings->size();
	for (auto it = readings->begin(); it != readings->end(); ++it)
	{
		if ((*it)->getId() > m_last_id)
			m_last_id = (*it)->getId();
		m_readings.push_back(*it);
	}
}

/**
 * Construct a reading set from a JSON document returned from
 * the Fledge storage service query or notification.
 *
 * @param json	The JSON document (as string) with readings data
 */
ReadingSet::ReadingSet(const std::string& json) : m_last_id(0)
{
	unsigned long rows = 0;
	Document doc;
	doc.Parse(json.c_str());
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
 */
void
ReadingSet::append(ReadingSet *readings)
{
	append(readings->getAllReadings());
	readings->clear();
}

/**
 * Append the readings in a second reading set to this reading set.
 * The readings are removed from the original reading set
 */
void
ReadingSet::append(ReadingSet& readings)
{
	append(readings.getAllReadings());
	readings.clear();
}

/**
 * Append a set of readings to this reading set.
 */
void
ReadingSet::append(const vector<Reading *>& readings)
{
	for (auto it = readings.cbegin(); it != readings.cend(); it++)
	{
		if ((*it)->getId() > m_last_id)
			m_last_id = (*it)->getId();
		m_readings.push_back(*it);
		m_count++;
	}
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
}

/**
 * Remove the readings from the vector without deleting them
 */
void
ReadingSet::clear()
{
	m_readings.clear();
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
		m_id = json["id"].GetUint();
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
			for (auto &m : json["reading"].GetObject()) {
				switch (m.value.GetType()) {
					// String
					case (kStringType): {
						DatapointValue value(m.value.GetString());
						this->addDatapoint(new Datapoint(m.name.GetString(),
										 value));
						break;
					}

						// Number
					case (kNumberType): {
						if (m.value.IsInt() ||
						    m.value.IsUint() ||
						    m.value.IsInt64() ||
						    m.value.IsUint64()) {

							DatapointValue *value;
							if (m.value.IsInt()) {
								value = new DatapointValue((long) m.value.GetInt());
							} else {
								// Handle Uint as 64 bits
								value = new DatapointValue((long) m.value.GetInt64());
							}
							this->addDatapoint(new Datapoint(m.name.GetString(),
											 *value));
							delete value;
							break;
						} else if (m.value.IsDouble()) {
							DatapointValue value(m.value.GetDouble());
							this->addDatapoint(new Datapoint(m.name.GetString(),
											 value));
							break;
						} else {
							string errMsg = "Cannot parse the numeric type";
							errMsg += " of reading element '";
							errMsg.append(m.name.GetString());
							errMsg += "'";

							throw new ReadingSetException(errMsg.c_str());
							break;
						}
					}

					case kArrayType:
					    {
						    vector<double> arrayValues;
						    for (auto& v : m.value.GetArray())
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
						    this->addDatapoint(new Datapoint(m.name.GetString(),
											 value));
						    break;
						    
					    }
					case kObjectType:
					    {
						    // TODO This should be recursive
						vector<Datapoint *> *obj = new vector<Datapoint *>;
						for (auto &mo : m.value.GetObject()) {
							switch (mo.value.GetType()) {
								// String
								case (kStringType): {
									DatapointValue value(mo.value.GetString());
									obj->push_back(new Datapoint(mo.name.GetString(),
													 value));
									break;
								}

									// Number
								case (kNumberType): {
									if (mo.value.IsInt() ||
									    mo.value.IsUint() ||
									    mo.value.IsInt64() ||
									    mo.value.IsUint64()) {

										DatapointValue *value;
										if (mo.value.IsInt() ||
										    mo.value.IsUint()) {
											value = new DatapointValue((long) mo.value.GetInt());
										} else {
											value = new DatapointValue((long) mo.value.GetInt64());
										}
										obj->push_back(new Datapoint(mo.name.GetString(),
														 *value));
										delete value;
										break;
									} else if (mo.value.IsDouble()) {
										DatapointValue value(mo.value.GetDouble());
										obj->push_back(new Datapoint(mo.name.GetString(),
														 value));
										break;
									} else {
										string errMsg = "Cannot parse the numeric type";
										errMsg += " of reading element '";
										errMsg.append(mo.name.GetString());
										errMsg += "'";

										throw new ReadingSetException(errMsg.c_str());
										break;
									}
								}

								case kArrayType:
								    {
									    vector<double> arrayValues;
									    for (auto& v : mo.value.GetArray())
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
									    obj->push_back(new Datapoint(mo.name.GetString(),
														 value));
									    break;
									    
								}
							}
						}
						DatapointValue value(obj, true);
						this->addDatapoint(new Datapoint(m.name.GetString(),
											 value));
					    break;
					    }

					default: {
						string errMsg = "Cannot handle unsupported type '";
					        errMsg += kTypeNames[m.value.GetType()];
						errMsg += "' of reading element '";
						errMsg.append(m.name.GetString());
						errMsg += "'";

						throw new ReadingSetException(errMsg.c_str());

						break;
					}
				}
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
 * Escapes a character in a string to be properly handled as JSON
 *
 */
void JSONReading::escapeCharacter(string& stringToEvaluate, string pattern)
{
	string escaped = "\\" + pattern;

	boost::replace_all(stringToEvaluate, pattern, escaped);
}
