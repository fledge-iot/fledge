/*
 * FogLAMP OSI Soft OMF interface to PI Server.
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Massimiliano Pinto
 */


#include <iostream>
#include <string>
#include <omf.h>
#include <logger.h>

using namespace std;

/**
 * OMFData constructor
 */
OMFData::OMFData(const Reading& reading)
{
	// Convert reading data into the OMF JSON string
	m_value.append("{\"containerid\": \"measurement_");
	m_value.append(reading.getAssetName() + "\", \"values\": [{");

	// Get reading data
	const vector<Datapoint*> data = reading.getReadingData();

	/**
	 * This loop creates:
	 * "dataName": {"type": "dataType"},
	 */
	for (vector<Datapoint*>::const_iterator it = data.begin(); it != data.end(); ++it)
	{
		// Add datapoint Name
		m_value.append("\"" + (*it)->getName() + "\": " + (*it)->getData().toString());
		m_value.append(", ");
	}

	// Append Z to getAssetDateTime(FMT_STANDARD)
	m_value.append("\"Time\": \"" + reading.getAssetDateTime(Reading::FMT_STANDARD) + "Z" + "\"");

	m_value.append("}]}");
}

/**
 * Return the (reference) JSON data in m_value
 */
const string& OMFData::OMFdataVal() const
{
	return m_value;
}

/**
 * OMF constructor
 */
OMF::OMF(HttpSender& sender,
	 const string& path,
	 const string& id,
	 const string& token) :
	 m_path(path),
	 m_typeId(id),
	 m_producerToken(token),
         m_sender(sender)
{
	m_lastError = false;
}

// Destructor
OMF::~OMF()
{
}

/**
 * Sends all the data type messages for a Reading data row
 *
 * @param row    The current Reading data row
 * @return       True is all data types have been sent (HTTP 200/204 OK)
 *               False when first error occurs.
 */
bool OMF::sendDataTypes(const Reading& row) const
{
	int res;

	// Create header for Type
	vector<pair<string, string>> resType = OMF::createMessageHeader("Type");
	// Create data for Type message	
	string typeData = OMF::createTypeData(row);

	// Build an HTTPS POST with 'resType' headers
	// and 'typeData' JSON payload
	// Then get HTTPS POST ret code and return 0 to client on error
	try
	{
		res = m_sender.sendRequest("POST", m_path, resType, typeData);
		if (res != 200 && res != 204)
		{
			Logger::getLogger()->error("Sending JSON dataType message 'Type' error: HTTP code |%d| - HostPort |%s| - path |%s| - message |%s|",
						   res,
						   m_sender.getHostPort().c_str(),
						   m_path.c_str(),
						   typeData.c_str() );
			return false;
		}
	}
	catch (const std::exception& e)
	{
                Logger::getLogger()->error("Sending JSON dataType message 'Type' error |%s| - HostPort |%s| - path |%s| - message |%s|",
                                           e.what(),
                                           m_sender.getHostPort().c_str(),
                                           m_path.c_str(),
                                           typeData.c_str() );

		return false;
	}

	// Create header for Container
	vector<pair<string, string>> resContainer = OMF::createMessageHeader("Container");
	// Create data for Container message	
	string typeContainer = OMF::createContainerData(row);

	// Build an HTTPS POST with 'resContainer' headers
	// and 'typeContainer' JSON payload
	// Then get HTTPS POST ret code and return 0 to client on error
	try
	{
		res = m_sender.sendRequest("POST", m_path, resContainer, typeContainer);
		if (res != 200 && res != 204)
		{
			Logger::getLogger()->error("Sending JSON dataType message 'Container' error: HTTP code %d", res);
			return false;
		}
	}
	catch (const std::exception& e)
	{
		Logger::getLogger()->error("Sending JSON dataType message 'Container' error: %s", e.what());
		return false;
	}

	// Create header for Static data
	vector<pair<string, string>> resStaticData = OMF::createMessageHeader("Data");
	// Create data for Static Data message	
	string typeStaticData = OMF::createStaticData(row);

	// Build an HTTPS POST with 'resStaticData' headers
	// and 'typeStaticData' JSON payload
	// Then get HTTPS POST ret code and return 0 to client on error
	try
	{
		res = m_sender.sendRequest("POST", m_path, resStaticData, typeStaticData);
		if (res != 200 && res != 204)
		{
			Logger::getLogger()->error("Sending JSON dataType message 'StaticData' error: HTTP code %d", res);
			return false;
		}
	}
	catch (const std::exception& e)
	{
		Logger::getLogger()->error("Sending JSON dataType message 'StaticData' error: %s", e.what());
		return false;
	}

	// Create header for Link data
	vector<pair<string, string>> resLinkData = OMF::createMessageHeader("Data");
	// Create data for Static Data message	
	string typeLinkData = OMF::createLinkData(row);

	// Build an HTTPS POST with 'resLinkData' headers
	// and 'typeLinkData' JSON payload
	// Then get HTTPS POST ret code and return 0 to client on error
	try
	{
		res = m_sender.sendRequest("POST", m_path, resLinkData, typeLinkData);
		if (res != 200 && res != 204)
		{
			Logger::getLogger()->error("Sending JSON dataType message 'Data' (lynk) error: %d", res);
			return false;
		}
		else
		{
			// All data types sent: success
			return true;
		}
	}
	catch (const std::exception& e)
	{
		Logger::getLogger()->error("Sending JSON dataType message 'Data' (lynk) error: %s", e.what());
		return false;
	}
}

/**
 * Send all the readings to the PI Server
 *
 * @param readings            A vector of readings data pointers
 * @param skipSendDataTypes   Send datatypes only once (default is true)
 * @return                    != on success, 0 otherwise
 */
uint32_t OMF::sendToServer(const vector<Reading *>& readings,
			   bool skipSentDataTypes)
{
	/*
	 * Iterate over readings:
	 * - Send/cache Types
	 * - transform a reading to OMF format
	 * - add OMND data to new vector
	 */

	ostringstream jsonData;
	jsonData << "[";

	// Fecth Reading* data
	for (vector<Reading *>::const_iterator elem = readings.begin();
						    elem != readings.end();
						    ++elem)
	{
		bool sendDataTypes;

		// Create the key for dataTypes sending once
		string key((**elem).getAssetName() + m_typeId);

		sendDataTypes = (m_lastError == false && skipSentDataTypes == true) ?
				 // Send if not already sent
				 !OMF::getCreatedTypes(key) :
				 // Always send types
				 true;

		// Handle the data types of the current reading
		if (sendDataTypes && !OMF::handleDataTypes(**elem, skipSentDataTypes))
		{
			// Failure
			m_lastError = true;
			return 0;
		}

		// Add into JSON string the OMF transformed Reading data
		jsonData << OMFData(**elem).OMFdataVal() << (elem < (readings.end() -1 ) ? ", " : "");
	}

	jsonData << "]";

	/**
	 * Types messages sent, now transorm ech reading to OMF format.
	 *
	 * After formatting the new vector of data can be sent
	 * with one message only
	 */

	// Create header for Readings data
	vector<pair<string, string>> readingData = OMF::createMessageHeader("Data");

	// Build an HTTPS POST with 'readingData headers
	// and 'allReadings' JSON payload
	// Then get HTTPS POST ret code and return 0 to client on error
	try
	{
		int res = m_sender.sendRequest("POST", m_path, readingData, jsonData.str());
		if (res != 200 && res != 204)
		{
			Logger::getLogger()->error("Sending JSON readings data error: %d", res);
			m_lastError = true;
			return 0;
		}

		m_lastError = false;

		// Return number of sen t readings to the caller
		return readings.size();
	}
	catch (const std::exception& e)
	{
		Logger::getLogger()->error("Sending JSON data error: %s", e.what());
		m_lastError = true;
		return 0;
	}
}

/**
 * Send all the readings to the PI Server
 *
 * @param readings            A vector of readings data
 * @param skipSendDataTypes   Send datatypes only once (default is true)
 * @return                    != on success, 0 otherwise
 */
uint32_t OMF::sendToServer(const vector<Reading>& readings,
			   bool skipSentDataTypes)
{
	/*
	 * Iterate over readings:
	 * - Send/cache Types
	 * - transform a reading to OMF format
	 * - add OMF data to new vector
	 */
	ostringstream jsonData;
	jsonData << "[";

	// Fecth Reading data
	for (vector<Reading>::const_iterator elem = readings.begin();
						    elem != readings.end();
						    ++elem)
	{
		bool sendDataTypes;

		// Create the key for dataTypes sending once
		string key((*elem).getAssetName() + m_typeId);

		sendDataTypes = (m_lastError == false && skipSentDataTypes == true) ?
				 // Send if not already sent
				 !OMF::getCreatedTypes(key) :
				 // Always send types
				 true;

		// Handle the data types of the current reading
		if (sendDataTypes && !OMF::handleDataTypes(*elem, skipSentDataTypes))
		{
			// Failure
			m_lastError = true;
			return 0;
		}

		// Add into JSON string the OMF transformed Reading data
		jsonData << OMFData(*elem).OMFdataVal() << (elem < (readings.end() -1 ) ? ", " : "");
	}

	jsonData << "]";

	// Build headers for Readings data
	vector<pair<string, string>> readingData = OMF::createMessageHeader("Data");

	// Build an HTTPS POST with 'readingData headers and 'allReadings' JSON payload
	// Then get HTTPS POST ret code and return 0 to client on error
	int res = m_sender.sendRequest("POST", m_path, readingData, jsonData.str());

	if (res != 200 && res != 204)
	{
		Logger::getLogger()->error("Sending JSON readings data error: %d", res);
		m_lastError = true;
		return 0;
	}

	m_lastError = false;

	// Return number of sen t readings to the caller
	return readings.size();
}

/**
 * Send a single reading to the PI Server
 *
 * @param reading             A reading to send
 * @return                    != on success, 0 otherwise
 */
uint32_t OMF::sendToServer(const Reading& reading,
			   bool skipSentDataTypes)
{
	return OMF::sendToServer(&reading, skipSentDataTypes);
}

/**
 * Send a single reading pointer to the PI Server
 *
 * @param reading             A reading pointer to send
 * @return                    != on success, 0 otherwise
 */
uint32_t OMF::sendToServer(const Reading* reading,
			   bool skipSentDataTypes)
{
	ostringstream jsonData;
	jsonData << "[";

	if (!OMF::handleDataTypes(*reading, skipSentDataTypes))
	{
		// Failure
		return 0;
	}

	// Add into JSON string the OMF transformed Reading data
	jsonData << OMFData(*reading).OMFdataVal();
	jsonData << "]";

	// Build headers for Readings data
	vector<pair<string, string>> readingData = OMF::createMessageHeader("Data");

	// Build an HTTPS POST with 'readingData headers and 'allReadings' JSON payload
	// Then get HTTPS POST ret code and return 0 to client on error
	int res = m_sender.sendRequest("POST", m_path, readingData, jsonData.str());

	if (res != 200 && res != 204)
	{
		return 0;
	}

	// Return number of sent readings to the caller
	return 1;
}

/**
 * Creates a vector of HTTP header to be sent to Server
 *
 * @param type    The message type ('Type', 'Container', 'Data')
 * @return        A vector of HTTP Header string pairs
 */
const vector<pair<string, string>> OMF::createMessageHeader(const std::string& type) const
{
	vector<pair<string, string>> res;

	res.push_back(pair<string, string>("messagetype", type));
	res.push_back(pair<string, string>("producertoken", m_producerToken));
	res.push_back(pair<string, string>("omfversion", "1.0"));
	res.push_back(pair<string, string>("messageformat", "JSON"));
	res.push_back(pair<string, string>("action", "create"));

	return  res; 
}

/**
 * Creates the Type message for data type definition
 *
 * @param reading    A reading data
 * @return           Type JSON message as string
 */
const std::string OMF::createTypeData(const Reading& reading) const
{
	// Build the Type data message (JSON Array)

	// Add the Static data part

	string tData("[{ \"type\": \"object\", \"properties\": { "
"\"Company\": {\"type\": \"string\"}, \"Location\": {\"type\": \"string\"}, "
"\"Name\": { \"type\": \"string\", \"isindex\": true } }, "
"\"classification\": \"static\", \"id\": \"");

	// Add type_id + '_' + asset_name + '_typename_sensor'
	OMF::setAssetTypeTag(reading.getAssetName(),
			     "typename_sensor",
			     tData);

	tData.append("\" }, { \"type\": \"object\", \"properties\": {");

	// Add the Dynamic data part

	/* We add for ech reading
	 * the DataPoint name & type
	 * type is 'integer' for INT
	 * 'number' for FLOAT
	 * 'string' for STRING
	 */

	const vector<Datapoint*> data = reading.getReadingData();

	/**
	 * This loop creates:
	 * "dataName": {"type": "dataType"},
	 */
	for (vector<Datapoint*>::const_iterator it = data.begin(); it != data.end(); ++it)
	{
	        string omfType = omfTypes[((*it)->getData()).getType()];
		string format = OMF::getFormatType(omfType);

		// Add datapoint Name
		tData.append("\"" + (*it)->getName() + "\"");
		tData.append(": {\"type\": \"");
		// Add datapoint Type
		tData.append(omfType);

		// Applies a format if it is defined
		if (! format.empty() ) {

			tData.append("\", \"format\": \"");
			tData.append(format);
		}

		tData.append("\"}, ");
	}

	// Add time field
	tData.append("\"Time\": {\"type\": \"string\", \"isindex\": true, \"format\": \"date-time\"}}, "
"\"classification\": \"dynamic\", \"id\": \"");

	// Add type_id + '_' + asset_name + '__typename_measurement'
	OMF::setAssetTypeTag(reading.getAssetName(),
			     "typename_measurement",
			     tData);

	 tData.append("\" }]");

	// Return JSON string
	return tData;
}

/**
 * Creates the Container message for data type definition
 *
 * @param reading    A reading data
 * @return           Type JSON message as string
 */
const std::string OMF::createContainerData(const Reading& reading) const
{
	// Build the Container data (JSON Array)
	string cData = "[{\"typeid\": \"";

	// Add type_id + '_' + asset_name + '__typename_measurement'
	OMF::setAssetTypeTag(reading.getAssetName(),
			     "typename_measurement",
			     cData);

	cData.append("\", \"id\": \"measurement_");
	cData.append(reading.getAssetName());
	cData.append("\"}]");

	// Return JSON string
	return cData;
}

/**
 * Creates the Static Data message for data type definition
 *
 * Note: type is 'Data'
 *
 * @param reading    A reading data
 * @return           Type JSON message as string
 */
const std::string OMF::createStaticData(const Reading& reading) const
{
	// Build the Static data (JSON Array)
	string sData = "[{\"typeid\": \"";

	// Add type_id + '_' + asset_name + '_typename_sensor'
	OMF::setAssetTypeTag(reading.getAssetName(),
			     "typename_sensor",
			     sData);

	sData.append("\", \"values\": [{\"Location\": \"Palo Alto\", "
"\"Company\": \"Dianomic\", \"Name\": \"");

	// Add asset_name
	sData.append(reading.getAssetName());
	sData.append("\"}]}]");

	// Return JSON string
	return sData;
}

/**
 * Creates the Link Data message for data type definition
 *
 * Note: type is 'Data'
 *
 * @param reading    A reading data
 * @return           Type JSON message as string
 */
const std::string OMF::createLinkData(const Reading& reading) const
{
	// Build the Link data (JSON Array)

	string lData = "[{\"typeid\": \"__Link\", \"values\": "
"[{\"source\": {\"typeid\": \"";

	// Add type_id + '_' + asset_name + '__typename_sensor'
	OMF::setAssetTypeTag(reading.getAssetName(),
			     "typename_sensor",
			     lData);

	lData.append("\", \"index\": \"_ROOT\"}, \"target\": {\"typeid\": \"");

	// Add type_id + '_' + asset_name + '__typename_sensor'
	OMF::setAssetTypeTag(reading.getAssetName(),
			     "typename_sensor",
			     lData);

	lData.append("\", \"index\": \"");

	// Add asset_name
	lData.append(reading.getAssetName());

	lData.append("\"}}, {\"source\": {\"typeid\": \"");

	// Add type_id + '_' + asset_name + '__typename_sensor'
	OMF::setAssetTypeTag(reading.getAssetName(),
			     "typename_sensor",
			     lData);

	lData.append("\", \"index\": \"");

	// Add asset_name
	lData.append(reading.getAssetName());

	lData.append("\"}, \"target\": {\"containerid\": \"measurement_");

	// Add asset_name
	lData.append(reading.getAssetName());

	lData.append("\"}}]}]");

	// Return JSON string
	return lData;
}

/**
 * Set the tag ID_XYZ_typename_sensor|typename_measurement
 *
 * @param assetName    The assetName
 * @param tagName      The tagName to append
 * @param data         The string to append result tag
 */
void OMF::setAssetTypeTag(const string& assetName,
			  const string& tagName,
			  string& data) const
{
	// Add type_id + '_' + asset_name + '_' + tagName'
	data.append(m_typeId + "_" + assetName +  "_" + tagName);
}

/**
 * Handles the OMF data types for the current Reading row
 * DataTypoes are created and sent only once per assetName + typeId
 * if skipSending is true
 *
 * @param row            The current Reading row with data
 * @param skipSending    Send once or always the data types
 * @return               True if data types have been sent or already sent.
 *                       False if the sending has failed.
 */ 
bool OMF::handleDataTypes(const Reading& row,
			  bool skipSending)
{
	// Create the key for dataTypes sending once
	const string key(skipSending ?  (row.getAssetName() + m_typeId) : "");

	// Check whether to create and send Data Types
	bool sendTypes = (skipSending == true) ?
			  // Send if not already sent
			  !OMF::getCreatedTypes(key) :
			  // Always send types
			  true;

	// Handle the data types of the current reading
	if (sendTypes && !OMF::sendDataTypes(row))
	{
		// Failure
		return false;
	}

	// We have sent types, we might save this.
	if (skipSending && sendTypes)
	{
		// Save datatypes key
		OMF::setCreatedTypes(key);
	}

	// Just for dubug right now
	//if (skipSending)
	//{
	//	cerr << "dataTypes for key [" << key << "]" <<
	//		(sendTypes ? " have been sent." : " already sent.") << endl;
	//}
	//else
	//{
	//	cerr << "dataTypes for typeId [" << m_typeId << "] have been sent." << endl;
	//}

	// Success
	return true;
}

/**
 * Add the key (assetName + m_typeId) into a map
 * That key is checked by getCreatedTypes in order
 * to send dataTypes only once
 *
 * @param key    The data tyepe key (assetName + m_typeId) from the Reading row
 * @return       Always true
 */
bool OMF::setCreatedTypes(const string& key)
{
	return m_createdTypes[key] = true;
}

/**
 * Get from createdTypes map the key (assetName + m_typeId)
 *
 * @param key    The data tyepe key (assetName + m_typeId) from the Reading row
 * @return       True is the key exists (aka dataTypes already sent)
 *               or false if not found.
 */
bool OMF::getCreatedTypes(const string& key)
{
	return m_createdTypes[key];
}

/**
 * Get from m_formatTypes map the key (OMF type + OMF format)
 *
 * @param key    The OMF type for which the format is requested
 * @return       The defined OMF format for the requested type
 *
 */
std::string OMF::getFormatType(const string &key) const
{
        string value;

        try
        {
                auto pos = m_formatTypes.find(key);
                value = pos->second;
        }
        catch (const std::exception& e)
        {
                Logger::getLogger()->error("Unable to find the OMF format for the type :" + key + ": - error: %s", e.what());
        }

        return value;
}

/**
 * Add the key (OMF type + OMF format) into a map
 *
 * @param key    The OMF type, key of the map
 * @param value  The OMF format to set for the specific OMF type
 *
 */
void OMF::setFormatType(const string &key, string &value)
{

	m_formatTypes[key] = value;
}

