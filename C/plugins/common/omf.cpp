#include <utility>

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
#include <cstring>
#include <omf.h>
#include <logger.h>
#include <zlib.h>

using namespace std;

// Cache for OMF data types
static std::map<std::string, bool>	OMFcreatedTypes;

/**
 * OMFData constructor
 */
OMFData::OMFData(const Reading& reading, const string& typeId)
{
	// Convert reading data into the OMF JSON string
	m_value.append("{\"containerid\": \"" + typeId + "measurement_");
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
	m_value.append("\"Time\": \"" + reading.getAssetDateUserTime(Reading::FMT_STANDARD) + "Z" + "\"");

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
	m_changeTypeId = false;
}

// Destructor
OMF::~OMF()
{
}

/**
 * Compress a string
 *
 * @param str			Input STL string that is to be compressed
 * @param compressionlevel	zlib/gzip Compression level
 * @return str			gzip compressed binary data
 */
std::string OMF::compress_string(const std::string& str,
                            int compressionlevel)
{
    const int windowBits = 15;
    const int GZIP_ENCODING = 16;

    z_stream zs;                        // z_stream is zlib's control structure
    memset(&zs, 0, sizeof(zs));

    if (deflateInit2(&zs, compressionlevel, Z_DEFLATED,
		 windowBits | GZIP_ENCODING, 8,
		 Z_DEFAULT_STRATEGY) != Z_OK)
        throw(std::runtime_error("deflateInit failed while compressing."));

    zs.next_in = (Bytef*)str.data();
    zs.avail_in = str.size();           // set the z_stream's input

    int ret;
    char outbuffer[32768];
    std::string outstring;

    // retrieve the compressed bytes blockwise
    do {
        zs.next_out = reinterpret_cast<Bytef*>(outbuffer);
        zs.avail_out = sizeof(outbuffer);

        ret = deflate(&zs, Z_FINISH);

        if (outstring.size() < zs.total_out) {
            // append the block to the output string
            outstring.append(outbuffer,
                             zs.total_out - outstring.size());
        }
    } while (ret == Z_OK);

    deflateEnd(&zs);

    if (ret != Z_STREAM_END) {          // an error occurred that was not EOF
        std::ostringstream oss;
        oss << "Exception during zlib compression: (" << ret << ") " << zs.msg;
        throw(std::runtime_error(oss.str()));
    }

    return outstring;
}

/**
 * Sends all the data type messages for a Reading data row
 *
 * @param row    The current Reading data row
 * @return       True is all data types have been sent (HTTP 200/204 OK)
 *               False when first error occurs.
 */
bool OMF::sendDataTypes(const Reading& row)
{
	int res;
	m_changeTypeId = false;

	// Create header for Type
	vector<pair<string, string>> resType = OMF::createMessageHeader("Type");
	// Create data for Type message	
	string typeData = OMF::createTypeData(row);

	// Build an HTTPS POST with 'resType' headers
	// and 'typeData' JSON payload
	// Then get HTTPS POST ret code and return 0 to client on error
	try
	{
		res = m_sender.sendRequest("POST",
					   m_path,
					   resType,
					   typeData);
		if (res != 200 && res != 202 && res != 204)
		{
			Logger::getLogger()->error("Sending JSON dataType message 'Type' "
						   "- error: HTTP code |%d| - HostPort |%s| - path |%s| - OMF message |%s|",
						   res,
						   m_sender.getHostPort().c_str(),
						   m_path.c_str(),
						   typeData.c_str() );
			return false;
		}
	}
	// Exception raised for HTTP 400 Bad Request
	catch (const BadRequest& e)
	{
		if (OMF::isDataTypeError(e.what()))
		{
			// Data type error: force type-id change
			m_changeTypeId = true;
		}
                Logger::getLogger()->warn("Sending JSON dataType message 'Type', "
					  "not blocking issue:  |%s| - message |%s| - HostPort |%s| - path |%s| - OMF message |%s|",
					   (m_changeTypeId ? "Data Type " : "" ),
                                           e.what(),
                                           m_sender.getHostPort().c_str(),
                                           m_path.c_str(),
                                           typeData.c_str() );
		return false;
	}
	catch (const std::exception& e)
	{
                Logger::getLogger()->error("Sending JSON dataType message 'Type' "
					   "- generic error: |%s| - HostPort |%s| - path |%s| - OMF message |%s|",
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
		res = m_sender.sendRequest("POST",
					   m_path,
					   resContainer,
					   typeContainer);
		if (res != 200 && res != 202 && res != 204)
		{
			Logger::getLogger()->error("Sending JSON dataType message 'Container' "
						   "- error: HTTP code |%d| - HostPort |%s| - path |%s| - OMF message |%s|",
						   res,
						   m_sender.getHostPort().c_str(),
						   m_path.c_str(),
						   typeContainer.c_str() );
			return false;
		}
	}
	// Exception raised fof HTTP 400 Bad Request
	catch (const BadRequest& e)
	{
		if (OMF::isDataTypeError(e.what()))
		{
			// Data type error: force type-id change
			m_changeTypeId = true;
		}
		Logger::getLogger()->warn("Sending JSON dataType message 'Container' "
					   "not blocking issue: |%s| - message |%s| - HostPort |%s| - path |%s| - OMF message |%s|",
					   (m_changeTypeId ? "Data Type " : "" ),
					   e.what(),
					   m_sender.getHostPort().c_str(),
					   m_path.c_str(),
					   typeContainer.c_str() );
		return false;
	}
	catch (const std::exception& e)
	{
		Logger::getLogger()->error("Sending JSON dataType message 'Container' "
					   "- generic error: |%s| - HostPort |%s| - path |%s| - OMF message |%s|",
					   e.what(),
					   m_sender.getHostPort().c_str(),
					   m_path.c_str(),
					   typeContainer.c_str() );
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
		res = m_sender.sendRequest("POST",
					   m_path,
					   resStaticData,
					   typeStaticData);
		if (res != 200 && res != 202 && res != 204)
		{
			Logger::getLogger()->error("Sending JSON dataType message 'StaticData' "
						   "- error: HTTP code |%d| - HostPort |%s| - path |%s| - OMF message |%s|",
						   res,
						   m_sender.getHostPort().c_str(),
						   m_path.c_str(),
						   typeStaticData.c_str() );
			return false;
		}
	}
	// Exception raised fof HTTP 400 Bad Request
	catch (const BadRequest& e)
	{
		if (OMF::isDataTypeError(e.what()))
		{
			// Data type error: force type-id change
			m_changeTypeId = true;
		}
		Logger::getLogger()->warn("Sending JSON dataType message 'StaticData'"
					   "not blocking issue: |%s| - message |%s| - HostPort |%s| - path |%s| - OMF message |%s|",
					   (m_changeTypeId ? "Data Type " : "" ),
					   e.what(),
					   m_sender.getHostPort().c_str(),
					   m_path.c_str(),
					   typeStaticData.c_str() );
		return false;
	}
	catch (const std::exception& e)
	{
		Logger::getLogger()->error("Sending JSON dataType message 'StaticData'"
					   "- generic error: |%s| - HostPort |%s| - path |%s| - OMF message |%s|",
					   e.what(),
					   m_sender.getHostPort().c_str(),
					   m_path.c_str(),
					   typeData.c_str() );
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
		res = m_sender.sendRequest("POST",
					   m_path,
					   resLinkData,
					   typeLinkData);
		if (res != 200 && res != 202 && res != 204)
		{
			Logger::getLogger()->error("Sending JSON dataType message 'Data' (lynk) "
						   "- error: HTTP code |%d| - HostPort |%s| - path |%s| - OMF message |%s|",
						   res,
						   m_sender.getHostPort().c_str(),
						   m_path.c_str(),
						   typeLinkData.c_str() );
			return false;
		}
		else
		{
			// All data types sent: success
			return true;
		}
	}
	// Exception raised fof HTTP 400 Bad Request
	catch (const BadRequest& e)
	{
		if (OMF::isDataTypeError(e.what()))
		{
			// Data type error: force type-id change
			m_changeTypeId = true;
		}
		Logger::getLogger()->warn("Sending JSON dataType message 'Data' (lynk) "
					   "not blocking issue: |%s| - message |%s| - HostPort |%s| - path |%s| - OMF message |%s|",
					   (m_changeTypeId ? "Data Type " : "" ),
					   e.what(),
					   m_sender.getHostPort().c_str(),
					   m_path.c_str(),
					   typeData.c_str() );
		return false;
	}
	catch (const std::exception& e)
	{
		Logger::getLogger()->error("Sending JSON dataType message 'Data' (lynk) "
					   "- generic error: |%s| - HostPort |%s| - path |%s| - OMF message |%s|",
					   e.what(),
					   m_sender.getHostPort().c_str(),
					   m_path.c_str(),
					   typeLinkData.c_str() );
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
			   bool compression, bool skipSentDataTypes)
{
	std::map<string, Reading*> superSetDataPoints;

	// Create a superset of all found datapoints for each assetName
	// the superset[assetName] is then passed to routines which handle
	// creation of OMF data types
	setMapObjectTypes(readings, superSetDataPoints);

	/*
	 * Iterate over readings:
	 * - Send/cache Types
	 * - transform a reading to OMF format
	 * - add OMF data to new vector
	 */

	// Used for logging
	string json_not_compressed;

	ostringstream jsonData;
	jsonData << "[";

	// Fetch Reading* data
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

		Reading* datatypeStructure = NULL;
		if (sendDataTypes)
		{
			// Get the supersetDataPoints for current assetName
			auto it = superSetDataPoints.find((**elem).getAssetName());
			if (it != superSetDataPoints.end())
			{
				datatypeStructure = (*it).second;
			}
		}

		// Check first we have supersetDataPoints for the current reading
		if ((sendDataTypes && datatypeStructure == NULL) ||
		    // Handle the data types of the current reading
		    (sendDataTypes &&
		    // Send data type
		    !OMF::handleDataTypes(*datatypeStructure, skipSentDataTypes) &&
		    // Data type not sent: 
		    (!m_changeTypeId ||
		     // Increment type-id and re-send data types
		     !OMF::handleTypeErrors(*datatypeStructure))))
		{
			// Remove all assets supersetDataPoints
			unsetMapObjectTypes(superSetDataPoints);

			// Failure
			m_lastError = true;
			return 0;
		}

		// Add into JSON string the OMF transformed Reading data
		jsonData << OMFData(**elem, m_typeId).OMFdataVal() <<
			    (elem < (readings.end() - 1 ) ? ", " : "");
	}

	// Remove all assets supersetDataPoints
	unsetMapObjectTypes(superSetDataPoints);

	jsonData << "]";

	string json = jsonData.str();

	if (compression)
	{
		json_not_compressed = json;
		json = compress_string(json);
	}

	/**
	 * Types messages sent, now transform each reading to OMF format.
	 *
	 * After formatting the new vector of data can be sent
	 * with one message only
	 */

	// Create header for Readings data
	vector<pair<string, string>> readingData = OMF::createMessageHeader("Data");
	if (compression)
		readingData.push_back(pair<string, string>("compression", "gzip"));

	// Build an HTTPS POST with 'readingData headers
	// and 'allReadings' JSON payload
	// Then get HTTPS POST ret code and return 0 to client on error
	try
	{
		int res = m_sender.sendRequest("POST",
					       m_path,
					       readingData,
					       json);
		if (res != 200 && res != 202 && res != 204)
		{
			Logger::getLogger()->error("Sending JSON readings, "
						   "- error: HTTP code |%d| - HostPort |%s| - path |%s| - OMF message |%s|",
						   res,
						   m_sender.getHostPort().c_str(),
						   m_path.c_str(),
						   json_not_compressed.c_str() );
			m_lastError = true;
			return 0;
		}
		// Reset error indicator
		m_lastError = false;

		// Return number of sent readings to the caller
		return readings.size();
	}
	// Exception raised fof HTTP 400 Bad Request
	catch (const BadRequest& e)
        {
		if (OMF::isDataTypeError(e.what()))
		{
			// Some assets have invalid or redefined data type
			// NOTE:
			//
			// 1- We consider this a NOT blocking issue.
			// 2- Type-id is not incremented
			// 3- Data Types cache is cleared: next sendData call
			//    will send data types again.
			Logger::getLogger()->warn("Sending JSON readings, "
						  "not blocking issue: |%s| - HostPort |%s| - path |%s| - OMF message |%s|",
						  e.what(),
						  m_sender.getHostPort().c_str(),
						  m_path.c_str(),
						  json_not_compressed.c_str() );
			// Reset OMF types cache
			OMF::clearCreatedTypes();
			// Reset error indicator
			m_lastError = false;

			// It returns size instead of 0 as the rows in the block should be skipped in case of an error
			// as it is considered a not blocking ones.
			return readings.size();
		}
		else
		{
			Logger::getLogger()->error("Sending JSON data error: |%s| - HostPort |%s| - path |%s| - OMF message |%s|",
			                           e.what(),
			                           m_sender.getHostPort().c_str(),
			                           m_path.c_str(),
			                           json_not_compressed.c_str());
		}
		// Failure
		m_lastError = true;
		return 0;
	}
	catch (const std::exception& e)
	{
		Logger::getLogger()->error("Sending JSON data error: |%s| - HostPort |%s| - path |%s| - OMF message |%s|",
					   e.what(),
					   m_sender.getHostPort().c_str(),
					   m_path.c_str(),
					   json_not_compressed.c_str() );
		// Failure
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

	// Fetch Reading data
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
		jsonData << OMFData(*elem, m_typeId).OMFdataVal() << (elem < (readings.end() -1 ) ? ", " : "");
	}

	jsonData << "]";

	// Build headers for Readings data
	vector<pair<string, string>> readingData = OMF::createMessageHeader("Data");

	// Build an HTTPS POST with 'readingData headers and 'allReadings' JSON payload
	// Then get HTTPS POST ret code and return 0 to client on error
	try
	{
		int res = m_sender.sendRequest("POST", m_path, readingData, jsonData.str());

		if (res != 200 && res != 202 && res != 204) {
			Logger::getLogger()->error("Sending JSON readings data "
						   "- error: HTTP code |%d| - HostPort |%s| - path |%s| - OMF message |%s|",
				res,
				m_sender.getHostPort().c_str(),
				m_path.c_str(),
                                jsonData.str().c_str() );

			m_lastError = true;
			return 0;
		}
	}
	catch (const std::exception& e)
	{
		Logger::getLogger()->error("Sending JSON readings data "
					   "- generic error: |%s| - HostPort |%s| - path |%s| - OMF message |%s|",
					   e.what(),
					   m_sender.getHostPort().c_str(),
					   m_path.c_str(),
					   jsonData.str().c_str() );

		return false;
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
	jsonData << OMFData(*reading, m_typeId).OMFdataVal();
	jsonData << "]";

	// Build headers for Readings data
	vector<pair<string, string>> readingData = OMF::createMessageHeader("Data");

	// Build an HTTPS POST with 'readingData headers and 'allReadings' JSON payload
	// Then get HTTPS POST ret code and return 0 to client on error
	try
	{

		int res = m_sender.sendRequest("POST", m_path, readingData, jsonData.str());

		if (res != 200 && res != 202 && res != 204)
		{
			Logger::getLogger()->error("Sending JSON readings data "
						   "- error: HTTP code |%d| - HostPort |%s| - path |%s| - OMF message |%s|",
						   res,
						   m_sender.getHostPort().c_str(),
						   m_path.c_str(),
						   jsonData.str().c_str() );

			return 0;
		}
	}
	catch (const std::exception& e)
	{
		Logger::getLogger()->error("Sending JSON readings data "
					   "- generic error: |%s| - HostPort |%s| - path |%s| - OMF message |%s|",
					   e.what(),
					   m_sender.getHostPort().c_str(),
					   m_path.c_str(),
					   jsonData.str().c_str() );

		return false;
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

	cData.append("\", \"id\": \"" + m_typeId + "measurement_");
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

	lData.append("\"}, \"target\": {\"containerid\": \"" + m_typeId + "measurement_");

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
	return OMFcreatedTypes[key] = true;
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
	return OMFcreatedTypes[key];
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

/**
 * Set the list of errors considered not blocking in the communication
 * with the PI Server
 */
void OMF::setNotBlockingErrors(std::vector<std::string>& notBlockingErrors)
{

	m_notBlockingErrors = notBlockingErrors;
}


/**
 * Increment type-id
 */
void OMF::incrementTypeId()
{
	unsigned int id = atol(m_typeId.c_str());
	m_typeId = to_string(++id);
}

/**
 * Clear OMF types cache
 */
void OMF::clearCreatedTypes()
{
	OMFcreatedTypes.clear();
}

/**
 * Check for invalid/redefinition data type error
 *
 * @param message       Server reply message for data type creation
 * @return              True for data type error, false otherwise
 */
bool OMF::isDataTypeError(const char* message)
{
	if (message)
	{
		string serverReply(message);

		for(string &item : m_notBlockingErrors) {

			if (serverReply.find(item) != std::string::npos)
			{
				return true;
			}
		}
	}
	return false;
}

/**
 * Send again Data Types of current readind data
 * with a new type-id
 *
 * NOTE: the m_typeId member variable value is incremented.
 *
 * @param reading       The current reading data
 * @return              True if data types with new-id
 *                      have been sent, false otherwise.
 */
bool OMF::handleTypeErrors(const Reading& reading)
{
	bool ret = true;

	// Increment type-id
	OMF::incrementTypeId();

	// Reset change type-id indicator
	m_changeTypeId = false;

	// Reset OMF types cache
	OMF::clearCreatedTypes();

	// Force re-send data types with a new type-id
	if (!OMF::handleDataTypes(reading,
				  false))
	{
		Logger::getLogger()->error("Failure re-sending JSON dataType messages "
					   "with new type-id=" + m_typeId);
		// Failure
		m_lastError = true;
		ret = false;
	}
	return ret;
}

/**
 * Create a superset data map for each reading and found datapoints
 *
 * The output map is filled with a Reading object containing
 * all the datapoints found for each asset in the inoput reading set.
 * The datapoint have a fake value based on the datapoint type
 *  
 * @param    readings		Current input readings data
 * @param    dataSuperSet	Map to store all datapoints for an assetname
 */
void OMF::setMapObjectTypes(const vector<Reading*>& readings,
			    std::map<std::string, Reading*>& dataSuperSet) const
{
	// Temporary map for [asset][datapoint] = type
	std::map<string, map<string, string>> readingAllDataPoints;

	// Fetch ALL Reading pointers in the input vecror
	// and create a map of [assetName][datapoint1 .. datapointN] = type
	for (vector<Reading *>::const_iterator elem = readings.begin();
						elem != readings.end();
						++elem)
	{
		// Get asset name
		string assetName = (**elem).getAssetName();
		// Get all datapoints
		const vector<Datapoint*> data = (**elem).getReadingData();
		// Iterate through datapoints
		for (vector<Datapoint*>::const_iterator it = data.begin();
							it != data.end();
							++it)
		{       
			string omfType = omfTypes[((*it)->getData()).getType()];
			string datapointName = (*it)->getName();
			auto itr = readingAllDataPoints.find(assetName);
			// Asset not found in the map
			if (itr == readingAllDataPoints.end())
			{
				// Set type of current datapoint for ssetName
				readingAllDataPoints[assetName][datapointName] = omfType;
			}
			else
			{
				// Asset found
				auto dpItr = (*itr).second.find(datapointName);
				// Datapoint not found
				if (dpItr == (*itr).second.end())
				{
					// Add datapointName/type to map with key assetName
					(*itr).second.emplace(datapointName, omfType);
				}
				else
				{
					if ((*dpItr).second.compare(omfType) != 0)
					{
						// Datapoint already set has changed type
						Logger::getLogger()->warn("Datapoint '" + datapointName + \
									  "' in asset '" + assetName + \
									  "' has changed type from '" + (*dpItr).second + \
									  " to " + omfType);
					}

					// Update datapointName/type to map with key assetName
					// 1- remove element
					(*itr).second.erase(dpItr);	
					// 2- Add new value
					readingAllDataPoints[assetName][datapointName] = omfType;
				}
			}
		}
	}

	// Loop now only the elements found in the per asset types map
	for (auto it = readingAllDataPoints.begin();
		  it != readingAllDataPoints.end();
		  ++it)
	{
		string assetName = (*it).first;
		vector<Datapoint *> values;
		// Set fake datapoints values
		for (auto dp = (*it).second.begin();
			  dp != (*it).second.end();
			  ++dp)
		{
			if ((*dp).second.compare(OMF_TYPE_FLOAT) == 0)
			{
				DatapointValue vDouble(0.1);
				values.push_back(new Datapoint((*dp).first, vDouble));
			}
			else if ((*dp).second.compare(OMF_TYPE_INTEGER) == 0)
			{
				DatapointValue vInt((long)1);
				values.push_back(new Datapoint((*dp).first, vInt));
			}
			else if ((*dp).second.compare(OMF_TYPE_STRING) == 0)
			{
				DatapointValue vString("v_str");
				values.push_back(new Datapoint((*dp).first, vString));
			}
		}

		// Add the superset Reading data with fake values
		dataSuperSet.emplace(assetName, new Reading(assetName, values));
	}
}

/**
 * Cleanup the mapped object types for input data
 *
 * @param    dataSuperSet	The  mapped object to cleanup
 */
void OMF::unsetMapObjectTypes(std::map<std::string, Reading*>& dataSuperSet) const
{
	// Remove all assets supersetDataPoints
	for (auto m = dataSuperSet.begin();
		  m != dataSuperSet.end();
		  ++m)
	{
		(*m).second->removeAllDatapoints();
		delete (*m).second;
	}
	dataSuperSet.clear();
}
