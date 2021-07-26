/*
 * Fledge OSI Soft OMF interface to PI Server.
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Massimiliano Pinto
 */

#include <utility>
#include <iostream>
#include <string>
#include <cstring>
#include <omf.h>
#include <OMFHint.h>
#include <logger.h>
#include <zlib.h>
#include <rapidjson/document.h>
#include "rapidjson/error/en.h"
#include "string_utils.h"
#include <plugin_api.h>
#include <string_utils.h>
#include <datapoint.h>
#include <thread>

#include <piwebapi.h>

#include <algorithm>
#include <vector>
#include <iterator>

using namespace std;
using namespace rapidjson;

static bool isTypeSupported(DatapointValue& dataPoint);

// 1 enable performance tracking
#define INSTRUMENT	0

#define  AFHierarchySeparator '/'
#define  AF_TYPES_SUFFIX       "-type"

// Handling escapes for AF Hierarchies
#define AFH_SLASH            "/"
#define AFH_SLASH_ESCAPE     "@/"
#define AFH_SLASH_ESCAPE_TMP "##"
#define AFH_ESCAPE_SEQ       "@@"
#define AFH_ESCAPE_CHAR      "@"

// Structures to generate and assign the 1st level of AF hierarchy if the end point is PI Web API
const char *AF_HIERARCHY_1LEVEL_TYPE = QUOTE(
	[
		{
			"id": "_placeholder_typeid_",
			"version": "1.0.0.0",
			"type": "object",
			"classification": "static",
			"properties": {
				"Name": {
					"type": "string",
					"isname": true
				},
				"AssetId": {
					"type": "string",
					"isindex": true
				}
			}
		}
	]
);

const char *AF_HIERARCHY_1LEVEL_STATIC = QUOTE(
	[
		{

			"typeid": "_placeholder_typeid_",
			"values": [
				{
				"Name": "_placeholder_Name_",
				"AssetId": "_placeholder_AssetId_"
				}
			]
		}
	]
);


const char *AF_HIERARCHY_LEVEL_LINK = QUOTE(
[
  {
    "typeid": "__Link",
	"values": [
		{
			"source": {
				"typeid": "_placeholder_src_type_",
				"index":  "_placeholder_src_idx_"
			},
			"target": {
				"typeid": "_placeholder_tgt_type_",
				"index":  "_placeholder_tgt_idx_"
			}
		}
	]
  }
]
);

const char *AF_HIERARCHY_1LEVEL_LINK = QUOTE(
	{
		"source": {
			"typeid": "_placeholder_src_type_",
			"index": "_placeholder_src_idx_"
		},
		"target": {
			"typeid": "_placeholder_tgt_type_",
			"index": "_placeholder_tgt_idx_"
		}
	}
);


/**
 * OMFData constructor
 */
OMFData::OMFData(const Reading& reading, string measurementId, const OMF_ENDPOINT PIServerEndpoint,const string&  AFHierarchyPrefix, OMFHints *hints)
{
	string outData;
	bool changed;

	Logger::getLogger()->debug("%s - measurementId :%s: ", __FUNCTION__, measurementId.c_str());

	// Apply any TagName hints to modify the containerid
	if (hints)
	{
		const std::vector<OMFHint *> omfHints = hints->getHints();
		for (auto it = omfHints.cbegin(); it != omfHints.cend(); it++)
		{
			if (typeid(**it) == typeid(OMFTagNameHint))
			{
				measurementId = (*it)->getHint();
				Logger::getLogger()->info("Using OMF TagName hint: %s", measurementId.c_str());
			}
			if (typeid(**it) == typeid(OMFTagHint))
			{
				measurementId = (*it)->getHint();
				Logger::getLogger()->info("Using OMF TagName hint: %s", measurementId.c_str());
			}
		}
	}

	// Convert reading data into the OMF JSON string
	outData.append("{\"containerid\": \"" + measurementId);
	outData.append("\", \"values\": [{");


	// Get reading data
	const vector<Datapoint*> data = reading.getReadingData();
	unsigned long skipDatapoints = 0;

	/**
	 * This loop creates:
	 * "dataName": {"type": "dataType"},
	 */
	for (vector<Datapoint*>::const_iterator it = data.begin(); it != data.end(); ++it)
	{
		string dpName = (*it)->getName();
		if (dpName.compare(OMF_HINT) == 0)
		{
			// Don't send the OMF Hint to the PI Server
			continue;
		}
		if (!isTypeSupported((*it)->getData()))
		{
			skipDatapoints++;;	
			continue;
		}
		else
		{
			// Add datapoint Name
			outData.append("\"" + OMF::ApplyPIServerNamingRulesObj(dpName, nullptr) + "\": " + (*it)->getData().toString());
			outData.append(", ");
		}
	}

	// Append Z to getAssetDateTime(FMT_STANDARD)
	outData.append("\"Time\": \"" + reading.getAssetDateUserTime(Reading::FMT_STANDARD) + "Z" + "\"");

	outData.append("}]}");

	// Append all, some or no datapoins
	if (!skipDatapoints ||
	    skipDatapoints < data.size())
	{
		m_value.append(outData);
	}
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
	 const long id,
	 const string& token) :
	 m_path(path),
	 m_typeId(id),
	 m_producerToken(token),
	 m_sender(sender)
{
	m_lastError = false;
	m_changeTypeId = false;
	m_OMFDataTypes = NULL;
}

/**
 * OMF constructor with per asset data types
 */

OMF::OMF(HttpSender& sender,
	 const string& path,
	 map<string, OMFDataTypes>& types,
	 const string& token) :
	 m_path(path),
	 m_OMFDataTypes(&types),
	 m_producerToken(token),
	 m_sender(sender)
{
	// Get starting type-id sequence or set the default value
	auto it = (*m_OMFDataTypes).find(FAKE_ASSET_KEY);
	m_typeId = (it != (*m_OMFDataTypes).end()) ?
		   (*it).second.typeId :
		   TYPE_ID_DEFAULT;

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
 * @return       True is all data types have been sent (HTTP 2xx OK)
 *               False when first error occurs.
 */
bool OMF::sendDataTypes(const Reading& row, OMFHints *hints)
{
	int res;
	m_changeTypeId = false;

	// Create header for Type
	vector<pair<string, string>> resType = OMF::createMessageHeader("Type");
	// Create data for Type message	
	string typeData = OMF::createTypeData(row, hints);

	// If Datatyope in Reading row is not supported, just return true
	if (typeData.empty())
	{
		return true;
	}
	else
	{
		// TODO: ADD LOG
	}

	// Build an HTTPS POST with 'resType' headers
	// and 'typeData' JSON payload
	// Then get HTTPS POST ret code and return 0 to client on error
	try
	{
		res = m_sender.sendRequest("POST",
					   m_path,
					   resType,
					   typeData);
		if  ( ! (res >= 200 && res <= 299) )
		{
			Logger::getLogger()->error("Sending JSON dataType message 'Type', HTTP code %d - %s %s",
						   res,
						   m_sender.getHostPort().c_str(),
						   m_path.c_str());
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
			string errorMsg = errorMessageHandler(e.what());

			Logger::getLogger()->warn("Sending dataType message 'Type', not blocking issue: %s %s - %s %s",
				(m_changeTypeId ? "Data Type " : "" ),
				errorMsg.c_str(),
				m_sender.getHostPort().c_str(),
				m_path.c_str());

		return false;
	}
	catch (const std::exception& e)
	{
		string errorMsg = errorMessageHandler(e.what());

		Logger::getLogger()->error("Sending dataType message 'Type', %s - %s %s",
									errorMsg.c_str(),
									m_sender.getHostPort().c_str(),
									m_path.c_str());

		return false;
	}

	// Create header for Container
	vector<pair<string, string>> resContainer = OMF::createMessageHeader("Container");
	// Create data for Container message	
	string typeContainer = OMF::createContainerData(row, hints);

	// Build an HTTPS POST with 'resContainer' headers
	// and 'typeContainer' JSON payload
	// Then get HTTPS POST ret code and return 0 to client on error
	try
	{
		res = m_sender.sendRequest("POST",
					   m_path,
					   resContainer,
					   typeContainer);
		if  ( ! (res >= 200 && res <= 299) )
		{
			Logger::getLogger()->error("Sending JSON dataType message 'Container' "
						   "- error: HTTP code |%d| - %s %s",
						   res,
						   m_sender.getHostPort().c_str(),
						   m_path.c_str() );
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
		string errorMsg = errorMessageHandler(e.what());

		Logger::getLogger()->warn("Sending JSON dataType message 'Container' "
					   "not blocking issue: |%s| - %s - %s %s",
					   (m_changeTypeId ? "Data Type " : "" ),
					   errorMsg.c_str(),
					   m_sender.getHostPort().c_str(),
					   m_path.c_str() );
		return false;
	}
	catch (const std::exception& e)
	{
		string errorMsg = errorMessageHandler(e.what());

		Logger::getLogger()->error("Sending JSON dataType message 'Container' - %s - %s %s",
					   errorMsg.c_str(),
					   m_sender.getHostPort().c_str(),
					   m_path.c_str());
		return false;
	}

	if (m_sendFullStructure) {


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
			if  ( ! (res >= 200 && res <= 299) )
			{
				Logger::getLogger()->error("Sending JSON dataType message 'StaticData' "
							   "- error: HTTP code |%d| - %s %s",
							   res,
							   m_sender.getHostPort().c_str(),
							   m_path.c_str() );
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
			string errorMsg = errorMessageHandler(e.what());

			Logger::getLogger()->warn("Sending JSON dataType message 'StaticData'"
						   "not blocking issue: |%s| - %s - %s %s",
						   (m_changeTypeId ? "Data Type " : "" ),
						   errorMsg.c_str(),
						   m_sender.getHostPort().c_str(),
						   m_path.c_str() );
			return false;
		}
		catch (const std::exception& e)
		{
			string errorMsg = errorMessageHandler(e.what());

			Logger::getLogger()->error("Sending JSON dataType message 'StaticData'"
						   "- generic error: %s -  %s %s",
						   errorMsg.c_str(),
						   m_sender.getHostPort().c_str(),
						   m_path.c_str() );
			return false;
		}
	}


	if (m_sendFullStructure)
	{
		// Create header for Link data
		vector<pair<string, string>> resLinkData = OMF::createMessageHeader("Data");

		string assetName = m_assetName;
		string AFHierarchyLevel;
		string prefix;
		string objectPrefix;

		auto rule = m_AssetNamePrefix.find(assetName);
		if (rule != m_AssetNamePrefix.end())
		{
			auto itemArray = rule->second;
			objectPrefix = "";

			for (auto &item : itemArray)
			{
				string AFHierarchy;
				string prefix;

				AFHierarchy = std::get<0>(item);
				generateAFHierarchyPrefixLevel(AFHierarchy, prefix, AFHierarchyLevel);

				prefix = std::get<1>(item);

				if (objectPrefix.empty())
				{
					objectPrefix = prefix;
				}

				Logger::getLogger()->debug("%s - assetName :%s: AFHierarchy :%s: prefix :%s: objectPrefix :%s:  AFHierarchyLevel :%s: ", __FUNCTION__
										   ,assetName.c_str()
										   , AFHierarchy.c_str()
										   , prefix.c_str()
										   , objectPrefix.c_str()
										   , AFHierarchyLevel.c_str() );

				// Create data for Static Data message
				string typeLinkData = OMF::createLinkData(row, AFHierarchyLevel, prefix, objectPrefix, hints);

				// Build an HTTPS POST with 'resLinkData' headers
				// and 'typeLinkData' JSON payload
				// Then get HTTPS POST ret code and return 0 to client on error
				try
				{
					res = m_sender.sendRequest("POST",
											   m_path,
											   resLinkData,
											   typeLinkData);
					if (!(res >= 200 && res <= 299))
					{
						Logger::getLogger()->error("Sending JSON dataType message 'Data' (lynk) - error: HTTP code |%d| - %s %s",
												   res,
												   m_sender.getHostPort().c_str(),
												   m_path.c_str());
						return false;
					}
				}
					// Exception raised fof HTTP 400 Bad Request
				catch (const BadRequest &e)
				{
					if (OMF::isDataTypeError(e.what()))
					{
						// Data type error: force type-id change
						m_changeTypeId = true;
					}
					string errorMsg = errorMessageHandler(e.what());

					Logger::getLogger()->warn("Sending JSON dataType message 'Data' (lynk) "
											  "not blocking issue: |%s| - %s - %s %s",
											  (m_changeTypeId ? "Data Type " : ""),
											  errorMsg.c_str(),
											  m_sender.getHostPort().c_str(),
											  m_path.c_str() );
					return false;
				}
				catch (const std::exception &e)
				{
					string errorMsg = errorMessageHandler(e.what());

					Logger::getLogger()->error("Sending JSON dataType message 'Data' (lynk) "
											   "- generic error: %s - %s %s",
											   errorMsg.c_str(),
											   m_sender.getHostPort().c_str(),
											   m_path.c_str() );
					return false;
				}
			}
		}
		else
		{
			Logger::getLogger()->error("AF hiererachy is not defined for the asset Name |%s|", assetName.c_str());
		}
	}
	// All data types sent: success
	return true;
}

/**
 * AFHierarchy - send an OMF message
 *
 * @param msgType    message type : Type, Data
 * @param jsonData   OMF message to send
 * @param action     action to be executed, either "create"or "delete"

 */
bool OMF::AFHierarchySendMessage(const string& msgType, string& jsonData, const std::string& action)
{
	bool success = true;
	int res = 0;
	string errorMessage;

	vector<pair<string, string>> resType = OMF::createMessageHeader(msgType, action);

	try
	{
		res = m_sender.sendRequest("POST", m_path, resType, jsonData);
		if  ( ! (res >= 200 && res <= 299) )
		{
			success = false;
		}
	}
	catch (const BadRequest& ex)
	{
		success = false;
		errorMessage = ex.what();
	}
	catch (const std::exception& ex)
	{
		success = false;
		errorMessage = ex.what();
	}

	if (! success)
	{
		string errorMsg = errorMessageHandler(errorMessage);

		if (res != 0)
			Logger::getLogger()->error("Sending Asset Framework hierarchy, %d %s - %s %s",
						   res,
						   errorMsg.c_str(),
						   m_sender.getHostPort().c_str(),
						   m_path.c_str());
		else
			Logger::getLogger()->error("Sending Asset Framework hierarchy, %s - %s %s",
							errorMsg.c_str(),
						   m_sender.getHostPort().c_str(),
						   m_path.c_str());

	}

	return success;
}

/**
 * AFHierarchy - handles OMF types definition
 *
 */
bool OMF::sendAFHierarchyTypes(const std::string AFHierarchyLevel, const std::string prefix)
{
	bool success;
	string jsonData;
	string tmpStr;

	jsonData = "";
	tmpStr = AF_HIERARCHY_1LEVEL_TYPE;
	StringReplace(tmpStr, "_placeholder_typeid_", prefix + "_" + AFHierarchyLevel + "_typeid");
	jsonData.append(tmpStr);

	success = AFHierarchySendMessage("Type", jsonData);

	return success;
}

/**
 *  AFHierarchy - handles OMF static data
 *
 */
bool OMF::sendAFHierarchyStatic(const std::string AFHierarchyLevel, const std::string prefix)
{
	bool success;
	string jsonData;
	string tmpStr;

	jsonData = "";
	tmpStr = AF_HIERARCHY_1LEVEL_STATIC;
	StringReplace(tmpStr, "_placeholder_typeid_"  , prefix + "_" + AFHierarchyLevel + "_typeid");
	StringReplace(tmpStr, "_placeholder_Name_"    , AFHierarchyLevel);
	StringReplace(tmpStr, "_placeholder_AssetId_" , prefix + "_" + AFHierarchyLevel);
	jsonData.append(tmpStr);

	success = AFHierarchySendMessage("Data", jsonData);

	return success;
}

/**
 *  AFHierarchy - creates the link between 2 elements in the AF hierarchy
 *
 */
bool OMF::sendAFHierarchyLink(std::string parent, std::string child, std::string prefixIdParent, std::string prefixId)
{
	bool success;
	string jsonData;
	string tmpStr;

	jsonData = "";
	tmpStr = AF_HIERARCHY_LEVEL_LINK;

	StringReplace(tmpStr, "_placeholder_src_type_", prefixIdParent + "_" + parent + "_typeid");
	StringReplace(tmpStr, "_placeholder_src_idx_",  prefixIdParent + "_" + parent );
	StringReplace(tmpStr, "_placeholder_tgt_type_", prefixId       + "_" + child + "_typeid");
	StringReplace(tmpStr, "_placeholder_tgt_idx_",  prefixId + "_" + child);
	jsonData.append(tmpStr);


	success = AFHierarchySendMessage("Data", jsonData);

	return success;
}

/**
 *  AFHierarchy - creates or delete the link between 2 elements in the AF hierarchy in relation to the parameter action
 *
 */
bool OMF::manageAFHierarchyLink(std::string parent, std::string child, std::string prefixIdParent, std::string prefixId, std::string childFull, string action)
{
	bool success;
	string jsonData;
	string tmpStr;

	jsonData = "";
	tmpStr = AF_HIERARCHY_LEVEL_LINK;

	StringReplace(tmpStr, "_placeholder_src_type_", prefixIdParent + "_" + parent + "_typeid");
	StringReplace(tmpStr, "_placeholder_src_idx_",  prefixIdParent + "_" + parent );

	if (childFull.empty()) {

		StringReplace(tmpStr, "_placeholder_tgt_type_", prefixId       + "_" + child + "_typeid");
	} else {
		StringReplace(tmpStr, "_placeholder_tgt_type_", childFull);
	}

	StringReplace(tmpStr, "_placeholder_tgt_idx_",  "A_" + prefixId + "_" + child);
	jsonData.append(tmpStr);

	success = AFHierarchySendMessage("Data", jsonData, action);

	return success;
}

/**
 *  AFHierarchy - delete the link between 2 elements in the AF hierarchy
 *
 */
void OMF::deleteAssetAFH(const string& assetName, string& path) {

	std::string pathLastLevel, pathPrefixId, assetNamePrefixId, assetNameFullId;

	assetNamePrefixId = getHashStored(assetName);
	generateAFHierarchyPrefixLevel(path, pathPrefixId, pathLastLevel);

	setAssetTypeTagNew(assetName, "typename_sensor", assetNameFullId);

	Logger::getLogger()->debug("%s - assetName :%s: childPrefixId :%s: pathStored :%s: parentLastLevel :%s: parentPrefixId :%s:  childFull :%s:"
		, __FUNCTION__
		, assetName.c_str()
		, assetNamePrefixId.c_str()
		, path.c_str()
		, pathLastLevel.c_str()
		, pathPrefixId.c_str()
		, assetNameFullId.c_str()
	);

	manageAFHierarchyLink(pathLastLevel, assetName, pathPrefixId, assetNamePrefixId, assetNameFullId, "delete");
}

/**
 *  AFHierarchy - create the link between 2 elements in the AF hierarchy
 *
 */
void OMF::createAssetAFH(const string& assetName, string& path) {

	std::string pathLastLevel, pathPrefixId, assetNamePrefixId, assetNameFullId;

	assetNamePrefixId = getHashStored(assetName);
	generateAFHierarchyPrefixLevel(path, pathPrefixId, pathLastLevel);

	setAssetTypeTagNew(assetName, "typename_sensor", assetNameFullId);

	Logger::getLogger()->debug("%s - assetName :%s: childPrefixId :%s: pathStored :%s: pathLastLevel :%s: pathPrefixId :%s:  childFull :%s:"
		, __FUNCTION__
		, assetName.c_str()
		, assetNamePrefixId.c_str()
		, path.c_str()
		, pathLastLevel.c_str()
		, pathPrefixId.c_str()
		, assetNameFullId.c_str()
	);

	manageAFHierarchyLink(pathLastLevel, assetName, pathPrefixId, assetNamePrefixId, assetNameFullId, "create");
}

/**
  * Creates the hierarchies tree in the AF as defined in the configuration item DefaultAFLocation
 * each level is separated by /
 * the implementation is available for PI Web API only
 * The hierarchy is created/recreated if an OMF type message is sent*
 *
 */
bool OMF::handleAFHierarchySystemWide() {

	bool success = true;
	std::string level;
	std::string previousLevel;
	string parentPath;
	parentPath = evaluateParentPath(m_DefaultAFLocation, AFHierarchySeparator);
	success = sendAFHierarchyLevels(parentPath, m_DefaultAFLocation, m_AFHierarchyLevel);

	return success;
}

/**
 * Creates all the AF hierarchies levels as requested by the input parameter
 * Creates the AF hierarchy if it was not already created
 *
 * @param AFHierarchy   Hierarchies levels to be created as relative or absolute path
 * @param out		    true if succeeded
 */
bool OMF::sendAFHierarchy(string AFHierarchy)
{
	bool success = true;
	string path;
	string dummy;
	string parentPath;


	if(find(m_afhHierarchyAlredyCreated.begin(), m_afhHierarchyAlredyCreated.end(), AFHierarchy) == m_afhHierarchyAlredyCreated.end()){

		Logger::getLogger()->debug("%s - path created :%s:", __FUNCTION__, AFHierarchy.c_str() );

		if (AFHierarchy.at(0) == '/')
		{
			// Absolute path
			path = AFHierarchy;
			parentPath = evaluateParentPath(path, AFHierarchySeparator);
		}
		else
		{
			// relative  path
			path = m_DefaultAFLocation + "/" + AFHierarchy;
			parentPath = m_DefaultAFLocation;
		}

		m_afhHierarchyAlredyCreated.push_back(AFHierarchy);

		success = sendAFHierarchyLevels(parentPath, path, dummy);
	} else {
		Logger::getLogger()->debug("%s - path already created :%s:", __FUNCTION__, AFHierarchy.c_str() );
	}

	return success;
}

/**
 * Creates all the AF hierarchies level as requested by the input parameter
 *
 * @param path	    Full path of hierarchies to create
 * @param out		last level of the created hierarchy
 */
bool OMF::sendAFHierarchyLevels(string parentPath, string path, std::string &lastLevel) {

	bool success;
	std::string level;
	std::string previousLevel;

	StringReplaceAll(path, AFH_ESCAPE_SEQ ,AFH_ESCAPE_CHAR);
	StringReplaceAll(path, AFH_SLASH_ESCAPE ,AFH_SLASH_ESCAPE_TMP);

	if (path.find(AFHierarchySeparator) == string::npos)
	{
		string prefixId;

		// only 1 single level of hierarchy
		StringReplaceAll(path, AFH_SLASH_ESCAPE_TMP ,AFH_SLASH);
		prefixId = generateUniquePrefixId(path);

		success = sendAFHierarchyTypes(path, prefixId);
		if (success)
		{
			success = sendAFHierarchyStatic(path,prefixId);
		}
		lastLevel = path;
	}
	else
	{
		string pathFixed;
		string parentPathFixed;
		string prefixId;
		string prefixIdParent;
		string previousLevelPath;
		string AFHierarchyLevel;
		string levelPath;

		pathFixed = StringSlashFix(path);
		std::stringstream pathStream(pathFixed);

		// multiple hierarchy levels
		while (std::getline(pathStream, level, AFHierarchySeparator))
		{
			StringReplaceAll(level, AFH_SLASH_ESCAPE_TMP ,AFH_SLASH);

			levelPath = previousLevelPath + AFHierarchySeparator + level;
			levelPath = StringSlashFix(levelPath);
			prefixId = generateUniquePrefixId(levelPath);

			success = sendAFHierarchyTypes(level, prefixId);
			if (success)
			{
				success = sendAFHierarchyStatic(level, prefixId);
			}

			// Creates the link between the AF level
			if (previousLevel != "")
			{
				parentPathFixed = StringSlashFix(previousLevelPath);
				prefixIdParent = generateUniquePrefixId(parentPathFixed);

				sendAFHierarchyLink(previousLevel, level, prefixIdParent, prefixId);
			}
			previousLevelPath = levelPath;
			previousLevel = level;
		}
		lastLevel = level;
	}

	return success;
}

/**
 * Handle the creation of AF hierarchies
 *
 * @param out		true if succeded
 */
bool OMF::handleAFHirerarchy()
{
	bool success = true;

	if (m_PIServerEndpoint == ENDPOINT_PIWEB_API)
	{

		success = handleAFHierarchySystemWide();
	}
	return success;
}

/**
 * Sets the value of the prefix used for the objects naming
 *
 */
void OMF::setAFHierarchy()
{
	std::string level;
	std::string AFLocation;

	AFLocation = m_DefaultAFLocation;
	if (m_PIServerEndpoint == ENDPOINT_PIWEB_API)
	{
		// Implementation onfly for PI Web API
		StringReplaceAll(AFLocation, AFH_ESCAPE_SEQ,   AFH_ESCAPE_CHAR);
		StringReplaceAll(AFLocation, AFH_SLASH_ESCAPE ,AFH_SLASH_ESCAPE_TMP);
		std::stringstream defaultAFLocation(AFLocation);

		if (AFLocation.find(AFHierarchySeparator) == string::npos)
		{
			// only 1 single level of hierarchy
			m_AFHierarchyLevel = AFLocation;
		}
		else
		{
			// multiple hierarchy levels
			while (std::getline(defaultAFLocation, level, AFHierarchySeparator))
			{
				;
			}
			m_AFHierarchyLevel = level;
		}
		StringReplaceAll(m_AFHierarchyLevel, AFH_SLASH_ESCAPE_TMP ,AFH_SLASH);
	}
}

/**
 * Send all the readings to the PI Server
 *
 * @param readings            A vector of readings data pointers
 * @param skipSendDataTypes   Send datatypes only once (default is true)
 * @return                    != on success, 0 otherwise
 * xxx
 */
uint32_t OMF::sendToServer(const vector<Reading *>& readings,
			   bool compression, bool skipSentDataTypes)
{
	bool AFHierarchySent = false;
	bool sendDataTypes;
	string keyComplete;
	string AFHierarchyPrefix;
	string AFHierarchyLevel;
	string measurementId;

	string varValue;
	string varDefault;
	bool variablePresent;

#if INSTRUMENT
	ostringstream threadId;
	threadId << std::this_thread::get_id();

	struct timeval	start, t1, t2, t3, t4, t5;

#endif


#if INSTRUMENT
	gettimeofday(&start, NULL);
#endif

	// Create a superset of all found datapoints for each assetName
	// the superset[assetName] is then passed to routines which handle
	// creation of OMF data types
	OMF::setMapObjectTypes(readings, m_SuperSetDataPoints);

#if INSTRUMENT
	gettimeofday(&t1, NULL);
#endif

	// Applies the PI-Server naming rules to the AF hierarchy
	{
		bool changed = false;
		string  origDefaultAFLocation;

		origDefaultAFLocation = m_DefaultAFLocation;
		m_DefaultAFLocation = ApplyPIServerNamingRulesPath(m_DefaultAFLocation, &changed);

		if (changed) {

			Logger::getLogger()->info("%s - AF hierarchy changed to follow PI-Server naming rules from :%s: to :%s:", __FUNCTION__, origDefaultAFLocation.c_str(), m_DefaultAFLocation.c_str() );
		}
	}

	/*
	 * Iterate over readings:
	 * - Send/cache Types
	 * - transform a reading to OMF format
	 * - add OMF data to new vector
	 */

	// Used for logging
	string json_not_compressed;

	string OMFHintAFHierarchyTmp;
	string OMFHintAFHierarchy;

	bool pendingSeparator = false;
	ostringstream jsonData;
	jsonData << "[";
	// Fetch Reading* data
	for (vector<Reading *>::const_iterator elem = readings.begin();
						    elem != readings.end();
						    ++elem)
	{
		Reading *reading = *elem;
		OMFHintAFHierarchy = "";

		// Fetch and parse any OMFHint for this reading
		Datapoint *hintsdp = reading->getDatapoint("OMFHint");
		OMFHints *hints = NULL;
		bool usingTagHint = false;
		long typeId = 0;
		if (hintsdp)
		{
			hints = new OMFHints(hintsdp->getData().toString());
			const vector<OMFHint *> omfHints = hints->getHints();
			for (auto it = omfHints.cbegin(); it != omfHints.cend(); it++)
			{
				if (typeid(**it) == typeid(OMFTagHint))
				{
					Logger::getLogger()->info("Using OMF Tag hint: %s", (*it)->getHint().c_str());
					keyComplete.append("_" + (*it)->getHint());
					usingTagHint = true;
					break;
				}

				varValue="";
				varDefault="";
				variablePresent=false;

				if (typeid(**it) == typeid(OMFAFLocationHint))
				{
					OMFHintAFHierarchyTmp = (*it)->getHint();
					OMFHintAFHierarchy = variableValueHandle(*reading, OMFHintAFHierarchyTmp);

					Logger::getLogger()->debug("%s - OMF AFHierarchy original value :%s: new :%s:"
						,__FUNCTION__
						,OMFHintAFHierarchyTmp.c_str()
						,OMFHintAFHierarchy.c_str() );
				}
			}
		}

		// Applies the PI-Server naming rules to the AssetName
		{

			bool changed;
			string assetNameFledge;

			assetNameFledge = reading->getAssetName();
			m_assetName = ApplyPIServerNamingRulesObj(assetNameFledge, &changed);
			if (changed) {

				Logger::getLogger()->info("%s -  3 Asset name changed to follow PI-Server naming rules from :%s: to :%s:", __FUNCTION__, assetNameFledge.c_str(), m_assetName.c_str() );
			}
		}

		// Since hints are attached to individual readings that are processed by the north plugin if an AFLocation
		// hint is present it will override any default AFLocation or AF Location rules defined in the north plugin configuration.
		if ( ! createAFHierarchyOmfHint(m_assetName, OMFHintAFHierarchy) ) {

			evaluateAFHierarchyRules(m_assetName, *reading);
		}

		if (m_PIServerEndpoint == ENDPOINT_CR  ||
			m_PIServerEndpoint == ENDPOINT_OCS ||
			m_PIServerEndpoint == ENDPOINT_EDS
			)
		{
			keyComplete = m_assetName;
		}
		else if (m_PIServerEndpoint == ENDPOINT_PIWEB_API)
		{
			if (getNamingScheme(m_assetName) == NAMINGSCHEME_CONCISE) {

				keyComplete = m_assetName;
			} else {
				retrieveAFHierarchyPrefixAssetName(m_assetName, AFHierarchyPrefix, AFHierarchyLevel);
				keyComplete = AFHierarchyPrefix + "_" + m_assetName;
			}
		}

		if (! usingTagHint)
		{
			/*
			 * Check the OMFHints, if there are any, to see if we have a 
			 * type name that should be used for this asset.
			 * We will still create the tyope, but the name will be fixed 
			 * as the value of this hint.
			 */
			bool usingTypeNameHint = false;
			if (hints)
			{
				const vector<OMFHint *> omfHints = hints->getHints();
				for (auto it = omfHints.cbegin(); it != omfHints.cend(); it++)
				{
					if (typeid(**it) == typeid(OMFTypeNameHint))
					{
						Logger::getLogger()->info("Using OMF TypeName hint: %s", (*it)->getHint().c_str());
						keyComplete.append("_" + (*it)->getHint());
						usingTypeNameHint = true;
						break;
					}
				}
			}

			if (! AFHierarchySent)
			{
				setAFHierarchy();
			}

			sendDataTypes = (m_lastError == false && skipSentDataTypes == true) ?
					 // Send if not already sent
					 !OMF::getCreatedTypes(keyComplete, *reading, hints) :
					 // Always send types
					 true;

			Reading* datatypeStructure = NULL;
			if (sendDataTypes && !usingTypeNameHint)
			{
				// Increment type-id of assetName in in memory cache
				OMF::incrementAssetTypeIdOnly(keyComplete);
				// Remove data and keep type-id
				OMF::clearCreatedTypes(keyComplete);

				// Get the supersetDataPoints for current assetName
				auto it = m_SuperSetDataPoints.find(m_assetName);
				if (it != m_SuperSetDataPoints.end())
				{
					datatypeStructure = (*it).second;
				}
			}

			if (m_sendFullStructure) {

				// The AF hierarchy is created/recreated if an OMF type message is sent
				// it sends the hierarchy once
				if (sendDataTypes and ! AFHierarchySent)
				{
					handleAFHirerarchy();

					AFHierarchySent = true;
				}
			}

			if (usingTypeNameHint)
			{
				if (sendDataTypes && !OMF::handleDataTypes(keyComplete,
								*reading, skipSentDataTypes, hints))
				{
					// Failure
					m_lastError = true;
					return 0;
				}
			}
			else
			{
				// Check first we have supersetDataPoints for the current reading
				if ((sendDataTypes && datatypeStructure == NULL) ||
				    // Handle the data types of the current reading
				    (sendDataTypes &&
				    // Send data type
				    !OMF::handleDataTypes(keyComplete, *datatypeStructure, skipSentDataTypes, hints) &&
				    // Data type not sent:
				    (!m_changeTypeId ||
				     // Increment type-id and re-send data types
				     !OMF::handleTypeErrors(keyComplete, *datatypeStructure, hints))))
				{
					// Remove all assets supersetDataPoints
					OMF::unsetMapObjectTypes(m_SuperSetDataPoints);

					// Failure
					m_lastError = true;
					return 0;
				}
			}

			// Create the key for dataTypes sending once
			typeId = OMF::getAssetTypeId(m_assetName);
		}

		measurementId = generateMeasurementId(m_assetName);

		string outData = OMFData(*reading, measurementId, m_PIServerEndpoint, AFHierarchyPrefix, hints ).OMFdataVal();
		if (!outData.empty())
		{
			jsonData << (pendingSeparator ? ", " : "") << outData;
			pendingSeparator = true;
		}

		if (hints)
		{
			delete hints;
		}
	}

#if INSTRUMENT
	gettimeofday(&t2, NULL);
#endif

	// Remove all assets supersetDataPoints
	OMF::unsetMapObjectTypes(m_SuperSetDataPoints);

	jsonData << "]";

	string json = jsonData.str();
	json_not_compressed = json;

	if (compression)
	{
		json = compress_string(json);
	}

#if INSTRUMENT
	gettimeofday(&t3, NULL);
#endif

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
		if  ( ! (res >= 200 && res <= 299) )
		{
			Logger::getLogger()->error("Sending JSON readings , "
						   "- error: HTTP code |%d| - %s %s",
						   res,
						   m_sender.getHostPort().c_str(),
						   m_path.c_str()
						   );
			m_lastError = true;
			return 0;
		}
		// Reset error indicator
		m_lastError = false;

#if INSTRUMENT
		gettimeofday(&t4, NULL);
#endif

#if INSTRUMENT
		struct timeval tm;
		double timeT1, timeT2, timeT3, timeT4, timeT5;

		timersub(&t1, &start, &tm);
		timeT1 = tm.tv_sec + ((double)tm.tv_usec / 1000000);

		timersub(&t2, &t1, &tm);
		timeT2 = tm.tv_sec + ((double)tm.tv_usec / 1000000);

		timersub(&t3, &t2, &tm);
		timeT3 = tm.tv_sec + ((double)tm.tv_usec / 1000000);

		timersub(&t4, &t3, &tm);
		timeT4 = tm.tv_sec + ((double)tm.tv_usec / 1000000);

		timersub(&t5, &t4, &tm);
		timeT5 = tm.tv_sec + ((double)tm.tv_usec / 1000000);

		Logger::getLogger()->debug("Timing seconds - thread :%s: - superSet :%6.3f: - Loop :%6.3f: - compress :%6.3f: - send data :%6.3f: - msg size |%d| - msg size compressed |%d| ",
								   threadId.str().c_str(),
								   timeT1,
								   timeT2,
								   timeT3,
								   timeT4,
								   json_not_compressed.length(),
								   json.length()
		);

#endif


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

			string errorMsg = errorMessageHandler(e.what());

			Logger::getLogger()->warn("Sending JSON readings, "
						  "not blocking issue: %s - %s %s",
						  errorMsg.c_str(),
						  m_sender.getHostPort().c_str(),
						  m_path.c_str());

			// Extract assetName from error message
			string assetName;
			if (m_PIServerEndpoint == ENDPOINT_CR)
			{
				assetName = OMF::getAssetNameFromError(e.what());
			}
			else if (m_PIServerEndpoint == ENDPOINT_PIWEB_API)
			{
				// Currently not implemented/supported as PI WEB API does not
				// report in the error message the asset causing the problem
				assetName = "";
			}

			if (assetName.empty())
			{
				Logger::getLogger()->warn("Sending JSON readings, "
										  "not blocking issue: assetName not found in error message, "
										  " no types redefinition");
			}
			else
			{
				// Remove data and keep type-id
				OMF::clearCreatedTypes(assetName);

				Logger::getLogger()->warn("Sending JSON readings, "
							  "not blocking issue: 'type-id' of assetName '%s' "
							  "has been set to %d "
							  "- %s %s",
							  assetName.c_str(),
							  OMF::getAssetTypeId(assetName),
							  m_sender.getHostPort().c_str(),
							  m_path.c_str()
							  );
			}

			// Reset error indicator
			m_lastError = false;

			// It returns size instead of 0 as the rows in the block should be skipped in case of an error
			// as it is considered a not blocking ones.
			return readings.size();
		}
		else
		{
			string errorMsg = errorMessageHandler(e.what());

			Logger::getLogger()->error("Sending JSON data error : %s - %s %s",
									   errorMsg.c_str(),
			                           m_sender.getHostPort().c_str(),
			                           m_path.c_str()
									   );
		}
		// Failure
		m_lastError = true;
		return 0;
	}
	catch (const std::exception& e)
	{
		string errorMsg = errorMessageHandler(e.what());

		Logger::getLogger()->error("Sending JSON data error : %s - %s %s",
						errorMsg.c_str(),
						m_sender.getHostPort().c_str(),
						m_path.c_str()
						);

		// Failure
		m_lastError = true;
		return 0;
	}
}

/**
 * Apply an handling on the error message in relation to the End Point
 *
 */
string OMF::errorMessageHandler(const string &msg)
{
	string errorMsg;

	if (m_PIServerEndpoint == ENDPOINT_PIWEB_API)
	{
		PIWebAPI piWeb;
		errorMsg = piWeb.errorMessageHandler(msg);

	} else {
		errorMsg = msg;
	}

	return(errorMsg);
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
	string measurementId;
	jsonData << "[";

	// Fetch Reading data
	for (vector<Reading>::const_iterator elem = readings.begin();
						    elem != readings.end();
						    ++elem)
	{
		bool sendDataTypes;
		OMFHints *hints = NULL;

		Datapoint *hintsdp = elem->getDatapoint(OMF_HINT);
		if (hintsdp)
		{
			hints = new OMFHints(hintsdp->getData().toString());
		}

		// Create the key for dataTypes sending once
		m_assetName = ApplyPIServerNamingRulesObj((*elem).getAssetName(), nullptr);
		long typeId = OMF::getAssetTypeId(m_assetName);
		string key(m_assetName);

		measurementId = generateMeasurementId(m_assetName);

		sendDataTypes = (m_lastError == false && skipSentDataTypes == true) ?
				 // Send if not already sent
				 !OMF::getCreatedTypes(key, (*elem), hints) :
				 // Always send types
				 true;

		// Handle the data types of the current reading
		if (sendDataTypes && !OMF::handleDataTypes(key, *elem, skipSentDataTypes, hints))
		{
			// Failure
			m_lastError = true;
			return 0;
		}

		// Add into JSON string the OMF transformed Reading data
		jsonData << OMFData(*elem, measurementId, m_PIServerEndpoint, m_AFHierarchyLevel, hints).OMFdataVal() << (elem < (readings.end() -1 ) ? ", " : "");
	}

	jsonData << "]";

	// Build headers for Readings data
	vector<pair<string, string>> readingData = OMF::createMessageHeader("Data");

	// Build an HTTPS POST with 'readingData headers and 'allReadings' JSON payload
	// Then get HTTPS POST ret code and return 0 to client on error
	try
	{
		int res = m_sender.sendRequest("POST", m_path, readingData, jsonData.str());

		if  ( ! (res >= 200 && res <= 299) ) {
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
	string measurementId;
	jsonData << "[";

	m_assetName = ApplyPIServerNamingRulesObj(reading->getAssetName(), nullptr);

	string key(m_assetName);
	measurementId = generateMeasurementId(m_assetName);


	Datapoint *hintsdp = reading->getDatapoint("OMFHint");
	OMFHints *hints = NULL;
	if (hintsdp)
	{
		hints = new OMFHints(hintsdp->getData().toString());
	}
	if (!OMF::handleDataTypes(key, *reading, skipSentDataTypes, hints))
	{
		// Failure
		return 0;
	}

	long typeId = OMF::getAssetTypeId(m_assetName);
	// Add into JSON string the OMF transformed Reading data
	jsonData << OMFData(*reading, measurementId, m_PIServerEndpoint, m_AFHierarchyLevel, hints).OMFdataVal();
	jsonData << "]";

	// Build headers for Readings data
	vector<pair<string, string>> readingData = OMF::createMessageHeader("Data");

	// Build an HTTPS POST with 'readingData headers and 'allReadings' JSON payload
	// Then get HTTPS POST ret code and return 0 to client on error
	try
	{

		int res = m_sender.sendRequest("POST", m_path, readingData, jsonData.str());

		if  ( ! (res >= 200 && res <= 299) )
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
		string errorMsg = errorMessageHandler(e.what());

		Logger::getLogger()->error("Sending JSON readings data "
					   "- generic error: %s - %s %s",
					   errorMsg.c_str(),
					   m_sender.getHostPort().c_str(),
					   m_path.c_str() );

		return false;
	}

	// Return number of sent readings to the caller
	return 1;
}

/**
 * Creates a vector of HTTP header to be sent to Server
 *
 * @param type    The message type ('Type', 'Container', 'Data')
 # @param action  Action to execute, either "create"or "delete"
 * @return        A vector of HTTP Header string pairs
 */
const vector<pair<string, string>> OMF::createMessageHeader(const std::string& type, const std::string& action) const
{
	vector<pair<string, string>> res;

	res.push_back(pair<string, string>("messagetype", type));
	res.push_back(pair<string, string>("producertoken", m_producerToken));
	res.push_back(pair<string, string>("omfversion", "1.0"));
	res.push_back(pair<string, string>("messageformat", "JSON"));
	res.push_back(pair<string, string>("action", action));

	return  res; 
}

/**
 * Creates the Type message for data type definition
 *
 * @param reading    A reading data
 * @return           Type JSON message as string
 */
const std::string OMF::createTypeData(const Reading& reading, OMFHints *hints)
{
	// Build the Type data message (JSON Array)

	string tData="[";

	if (m_sendFullStructure) {

		// Add the Static data part
		tData.append("{ \"type\": \"object\", \"properties\": { ");
		for (auto it = m_staticData->cbegin(); it != m_staticData->cend(); ++it)
		{
			tData.append("\"");
			tData.append(ApplyPIServerNamingRulesObj(it->first.c_str(), nullptr) );
			tData.append("\": {\"type\": \"string\"},");
		}

		// Connector relay / ODS / EDS
		if (m_PIServerEndpoint == ENDPOINT_CR  ||
			m_PIServerEndpoint == ENDPOINT_OCS ||
			m_PIServerEndpoint == ENDPOINT_EDS
		   )
		{
			tData.append("\"Name\": { \"type\": \"string\", \"isindex\": true } }, "
						 "\"classification\": \"static\", \"id\": \"");
		}
		else if (m_PIServerEndpoint == ENDPOINT_PIWEB_API)
		{
			tData.append("\"Name\": { \"type\": \"string\", \"isname\": true }, ");
			tData.append("\"AssetId\": { \"type\": \"string\", \"isindex\": true } ");
			tData.append(" }, \"classification\": \"static\", \"id\": \"");
		}

		// Add type_id + '_' + asset_name + '_typename_sensor'
		OMF::setAssetTypeTag(m_assetName,
					 "typename_sensor",
					 tData);

		tData.append("\" }, ");
	}

	// Add the Dynamic data part
	tData.append(" { \"type\": \"object\", \"properties\": {");

	/* We add for each reading
	 * the DataPoint name & type
	 * type is 'integer' for INT
	 * 'number' for FLOAT
	 * 'string' for STRING
	 */

	bool ret = true;
	const vector<Datapoint*> data = reading.getReadingData();

	/**
	 * This loop creates:
	 * "dataName": {"type": "dataType"},
	 */
	for (vector<Datapoint*>::const_iterator it = data.begin(); it != data.end(); ++it)
	{
		string dpName = (*it)->getName();
		if (dpName.compare(OMF_HINT) == 0)
		{
			// We never include OMF hints in the data we send to PI
			continue;
		}
		string omfType;
		if (!isTypeSupported( (*it)->getData()))
		{
			omfType = OMF_TYPE_UNSUPPORTED;
		}
		else
		{
	        	omfType = omfTypes[((*it)->getData()).getType()];
		}
		string format = OMF::getFormatType(omfType);
		if (hints && (omfType == OMF_TYPE_FLOAT || omfType == OMF_TYPE_INTEGER))
		{
			const vector<OMFHint *> omfHints = hints->getHints(dpName);
			for (auto it = omfHints.cbegin(); it != omfHints.cend(); it++)
			{
				if (typeid(**it) == typeid(OMFNumberHint))
				{
					format = (*it)->getHint();
					break;
				}
				if (typeid(**it) == typeid(OMFIntegerHint))
				{
					omfType = OMF_TYPE_INTEGER;
					format = (*it)->getHint();
					break;
				}

			}
		}

		if (format.compare(OMF_TYPE_UNSUPPORTED) == 0)
		{
			//TO DO: ADD LOG
			ret = false;
			continue;
		}
		// Add datapoint Name
		tData.append("\"" + ApplyPIServerNamingRulesObj(dpName, nullptr) + "\"");
		tData.append(": {\"type\": \"");
		// Add datapoint Type
		tData.append(omfType);

		tData.append("\", \"name\": \"");
		tData.append(ApplyPIServerNamingRulesObj(dpName, nullptr) );

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

	bool typeNameSet = false;
	if (hints)
	{
		const vector<OMFHint *> omfHints = hints->getHints();
		for (auto it = omfHints.cbegin(); it != omfHints.cend(); it++)
		{
			if (typeid(**it) == typeid(OMFTypeNameHint))
			{
					Logger::getLogger()->info("Using OMF TypeName hint: %s", (*it)->getHint().c_str());
				tData.append((*it)->getHint());
				typeNameSet = true;
				break;
			}
		}
	}

	if (!typeNameSet)
	{
		// Add type_id + '_' + asset_name + '__typename_measurement'
		OMF::setAssetTypeTag(m_assetName,
				     "typename_measurement",
				     tData);
	}

	tData.append("\" }]");

	// Check we have to return empty data or not
	if (!ret && data.size() == 1)
	{
		// TODO: ADD LOGGING
		return string("");
	}
	else
	{
		// Return JSON string
		return tData;
	}
}

/**
 * Creates the Container message for data type definition
 *
 * @param reading    A reading data
 * @return           Type JSON message as string
 */
const std::string OMF::createContainerData(const Reading& reading, OMFHints *hints)
{
	string assetName = m_assetName;

	string measurementId;

	// Build the Container data (JSON Array)
	string cData = "[{\"typeid\": \"";

	string typeName = "";
	if (hints)
	{
		const std::vector<OMFHint *> omfHints = hints->getHints();
		for (auto it = omfHints.cbegin(); it != omfHints.cend(); it++)
		{
			if (typeid(**it) == typeid(OMFTypeNameHint))
			{
				typeName = (*it)->getHint();
				Logger::getLogger()->info("Using OMF TypeName hint: %s", typeName.c_str());
			}
		}
	}
	if (typeName.length())
	{
		cData.append(typeName);
	}
	else
	{
		// Add type_id + '_' + asset_name + '__typename_measurement'
		OMF::setAssetTypeTag(assetName,
				     "typename_measurement",
				     cData);
	}

	measurementId = generateMeasurementId(assetName);

	// Apply any TagName hints to modify the containerid
	if (hints)
	{
		const std::vector<OMFHint *> omfHints = hints->getHints();
		for (auto it = omfHints.cbegin(); it != omfHints.cend(); it++)
		{
			if (typeid(**it) == typeid(OMFTagNameHint))
			{
				measurementId = (*it)->getHint();
				Logger::getLogger()->info("Using OMF TagName hint: %s", measurementId.c_str());
				break;
			}
		}
	}

	cData.append("\", \"id\": \"" + measurementId);
	cData.append("\"}]");

	// Return JSON string
	return cData;
}

/**
 * Generate the container id for the given asset
 *
 * @param assetName  Asset for quick the container id should be generated
 * @return           Container it for the requested asset
 */
std::string OMF::generateMeasurementId(const string& assetName)
{
	std::string measurementId;

	string AFHierarchyPrefix;
	string AFHierarchyLevel;
	long namingScheme;
	long typeId;

	typeId = OMF::getAssetTypeId(assetName);

	namingScheme = getNamingScheme(assetName);

	if (namingScheme == NAMINGSCHEME_COMPATIBILITY ||
		namingScheme == NAMINGSCHEME_HASH)
	{
		measurementId = to_string(typeId) + "measurement_" + assetName;

		// Add the 1st level of AFHierarchy as a prefix to the name in case of PI Web API
		if (m_PIServerEndpoint == ENDPOINT_PIWEB_API)
		{
			retrieveAFHierarchyPrefixAssetName(assetName, AFHierarchyPrefix, AFHierarchyLevel);

			measurementId = AFHierarchyPrefix + "_" + measurementId;
		}
	} else {
		if (typeId > 1)
		{
			measurementId = to_string(typeId) + "measurement_" + assetName;
		} else {

			measurementId = assetName;
		}

	}

	Logger::getLogger()->debug("%s - mamingScheme default :%ld: namingScheme applied :%ld:  assetName :%s: typeId :%ld: measurementId :%s:",
							   __FUNCTION__,
							   m_NamingScheme,
							   namingScheme,
							   assetName.c_str(), 
							   typeId, 
							   measurementId.c_str() );

	return(measurementId);
}


/**
 * Generate a suffix for the given asset in relation to the selected naming schema and the value of the type id
 *
 * @param assetName  Asset for quick the suffix should be generated
 * @param typeId     TYpe id of the asset
 * @return           Suffix to be used for the given asset
 */
std::string OMF::generateSuffixType(string &assetName, long typeId)
{
	std::string suffix;
	long namingScheme;

	namingScheme = getNamingScheme(assetName);

	if (namingScheme == NAMINGSCHEME_COMPATIBILITY ||
		namingScheme == NAMINGSCHEME_SUFFIX)
	{
		suffix = AF_TYPES_SUFFIX + to_string(typeId);

	} else {
		if (typeId > 1)
		{
			suffix = AF_TYPES_SUFFIX + to_string(typeId);
		}

	}

	Logger::getLogger()->debug("%s - mamingScheme default :%ld: namingScheme applied :%ld: typeId :%ld: suffix :%s:",
		__FUNCTION__, 
		m_NamingScheme,
		namingScheme,
		typeId, 
		suffix.c_str());

	return(suffix);
}


/**
 * Creates the Static Data message for data type definition
 *
 * Note: type is 'Data'
 *
 * @param reading    A reading data
 * @return           Type JSON message as string
 */
const std::string OMF::createStaticData(const Reading& reading)
{
	string assetName;
	// Build the Static data (JSON Array)
	string sData = "[";

	sData.append("{\"typeid\": \"");

	assetName = m_assetName;

	long typeId = getAssetTypeId(assetName);

	// Add type_id + '_' + asset_name + '_typename_sensor'
	OMF::setAssetTypeTag(assetName,
			     "typename_sensor",
			     sData);

	sData.append("\", \"values\": [{");
	for (auto it = m_staticData->cbegin(); it != m_staticData->cend(); ++it)
	{
		sData.append("\"");
		sData.append(ApplyPIServerNamingRulesObj(it->first.c_str(), nullptr) );
		sData.append("\": \"");
		sData.append(it->second.c_str());
		sData.append("\", ");
	}
	sData.append(" \"Name\": \"");

	// Add asset_name
	// Connector relay / ODS / EDS
	if (m_PIServerEndpoint == ENDPOINT_CR)
	{
		sData.append(assetName);

	}
	else if (m_PIServerEndpoint == ENDPOINT_OCS ||
	         m_PIServerEndpoint == ENDPOINT_EDS)
	{
		sData.append(assetName);

	}
	else if (m_PIServerEndpoint == ENDPOINT_PIWEB_API)
	{
		string AFHierarchyPrefix;
		string AFHierarchyLevel;

		retrieveAFHierarchyPrefixAssetName(assetName, AFHierarchyPrefix, AFHierarchyLevel);

		sData.append(assetName + generateSuffixType(assetName, typeId));
		sData.append("\", \"AssetId\": \"");
		sData.append("A_" + AFHierarchyPrefix + "_" + assetName + generateSuffixType(assetName, typeId) );
	}

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
std::string OMF::createLinkData(const Reading& reading,  std::string& AFHierarchyLevel, std::string&  AFHierarchyPrefix, std::string&  objectPrefix, OMFHints *hints)
{
	string targetTypeId;

	string measurementId;

	string assetName = m_assetName;

	// Build the Link data (JSON Array)

	long typeId = getAssetTypeId(assetName);

	string lData = "[{\"typeid\": \"__Link\", \"values\": [";

	// Handles the structure for the Connector Relay
	// not supported by PI Web API
	// Connector relay / ODS / EDS
	if (m_PIServerEndpoint == ENDPOINT_CR  ||
		m_PIServerEndpoint == ENDPOINT_OCS ||
		m_PIServerEndpoint == ENDPOINT_EDS
		)
	{
		lData.append("{\"source\": {\"typeid\": \"");

		// Add type_id + '_' + asset_name + '__typename_sensor'
		OMF::setAssetTypeTag(assetName,
				     "typename_sensor",
				     lData);

		lData.append("\", \"index\": \"_ROOT\"},");
		lData.append("\"target\": {\"typeid\": \"");

		// Add type_id + '_' + asset_name + '__typename_sensor'
		OMF::setAssetTypeTag(assetName,
				     "typename_sensor",
				     lData);

		lData.append("\", \"index\": \"");

		// Add asset_name
		lData.append(assetName);

		lData.append("\"}},");
	}
	else if (m_PIServerEndpoint == ENDPOINT_PIWEB_API)
	{
		// Link the asset to the 1st level of AF hierarchy if the end point is PI Web API

		string tmpStr = AF_HIERARCHY_1LEVEL_LINK;

		OMF::setAssetTypeTag(assetName, "typename_sensor", targetTypeId);

		StringReplace(tmpStr, "_placeholder_src_type_", AFHierarchyPrefix + "_" + AFHierarchyLevel + "_typeid");
		StringReplace(tmpStr, "_placeholder_src_idx_",  AFHierarchyPrefix + "_" + AFHierarchyLevel );
		StringReplace(tmpStr, "_placeholder_tgt_type_", targetTypeId);
		StringReplace(tmpStr, "_placeholder_tgt_idx_", "A_" + objectPrefix + "_" + assetName +
			generateSuffixType(assetName, typeId) );

		lData.append(tmpStr);
		lData.append(",");
	}

	lData.append("{\"source\": {\"typeid\": \"");

	// Add type_id + '_' + asset_name + '__typename_sensor'
	OMF::setAssetTypeTag(assetName,
			     "typename_sensor",
			     lData);

	lData.append("\", \"index\": \"");

	if (m_PIServerEndpoint == ENDPOINT_CR)
	{
		// Add asset_name
		lData.append(assetName);
	}
	else if (m_PIServerEndpoint == ENDPOINT_OCS ||
			 m_PIServerEndpoint == ENDPOINT_EDS)
	{
		// Add asset_name
		lData.append(assetName);
	}
	else if (m_PIServerEndpoint == ENDPOINT_PIWEB_API)
	{
		lData.append("A_" + objectPrefix + "_" + assetName + generateSuffixType(assetName, typeId) );
	}

	measurementId = generateMeasurementId(assetName);

	// Apply any TagName hints to modify the containerid
	if (hints)
	{
		const std::vector<OMFHint *> omfHints = hints->getHints();
		for (auto it = omfHints.cbegin(); it != omfHints.cend(); it++)
		{
			if (typeid(**it) == typeid(OMFTagNameHint))
			{
				measurementId = (*it)->getHint();
				Logger::getLogger()->info("Using OMF TagName hint: %s", measurementId.c_str());
				break;
			}
		}
	}

	lData.append("\"}, \"target\": {\"containerid\": \"" + measurementId);

	lData.append("\"}}]}]");

	// Return JSON string
	return lData;
}

/**
 * Calculate the prefix to be used for AF objects and the last level of the hiererachies
 * from a given AF path
 *
 * @param path                   Path to evaluate
 * @param out/prefix		     Calculated prefix
 * @param out/AFHierarchyLevel   last level of the hiererachies evaluated form the path
 */
void OMF::generateAFHierarchyPrefixLevel(string& path, string& prefix, string& AFHierarchyLevel)
{
	string pathFixed;

	AFHierarchyLevel = extractLastLevel(path, AFHierarchySeparator);

	pathFixed = StringSlashFix(path);
	prefix = generateUniquePrefixId(pathFixed);
}


/**
 * Retrieve from the map the prefix and the last level of the hierarchy from a given assetname
 *
 * @param path                   assetName to evaluate
 * @param out/prefix		     Calculated prefix
 * @param out/AFHierarchyLevel   Last level of the hierarchy
 */
void OMF::retrieveAFHierarchyPrefixAssetName(const string& assetName, string& prefix, string& AFHierarchyLevel)
{
	string AFHierarchy;
	string prefixTmp;

	// Metadata Rules - Exist
	auto rule = m_AssetNamePrefix.find(assetName);
	if (rule != m_AssetNamePrefix.end())
	{
		AFHierarchy = std::get<0>(rule->second[0]);
		generateAFHierarchyPrefixLevel(AFHierarchy, prefixTmp, AFHierarchyLevel);

		prefix =std::get<1>(rule->second[0]);

	}

}

/**
 * Retrieve from the map the prefix and the hierarchy name from a given assetname
 *
 * @param path                   assetName to evaluate
 * @param out/prefix		     Calculated prefix
 * @param out/AFHierarchyLevel   hierarchy name
 */
void OMF::retrieveAFHierarchyFullPrefixAssetName(const string& assetName, string& prefix, string& AFHierarchy)
{
	string path;
	// Metadata Rules - Exist
	auto rule = m_AssetNamePrefix.find(assetName);
	if (rule != m_AssetNamePrefix.end())
	{
		AFHierarchy = std::get<0>(rule->second[0]);
		prefix =std::get<1>(rule->second[0]);

	}

}

/**
 * Handle the OMF hint AFLocation to defined a position of the asset into the AF hierarchy
 *
 * @param assetName              AssetName to handle
 * @param OmfHintHierarchy		 Position of the asset into the AF hierarchy
 *
 * @return                       True if set asset will have a defined AF hierarchy position
 */
bool OMF::createAFHierarchyOmfHint(const string& assetName, const  string &OmfHintHierarchy)
{
	string pathNew;
	string prefix;
	string AFHierarchyLevel;

	string prefixStored;
	string pathStored;

	bool ruleMatched = false;

	if (! OmfHintHierarchy.empty())
	{

		pathNew = OmfHintHierarchy;

		if (pathNew.at(0) != '/')
		{
			// relative  path
			pathNew = "/" + pathNew;
		}
		generateAFHierarchyPrefixLevel(pathNew, prefix, AFHierarchyLevel);
		ruleMatched = true;

		prefixStored = getHashStored (assetName);
		pathStored = getPathStored (assetName);

		Logger::getLogger()->debug("%s - OMF hint hierarchy - assetName :%s: path :%s: pathStored :%s: prefixStored :%s: "
			, __FUNCTION__
			, assetName.c_str()
			, pathNew.c_str()
			, pathStored.c_str()
			, prefixStored.c_str()
			);

		if(find(m_afhHierarchyAlredyCreated.begin(), m_afhHierarchyAlredyCreated.end(), pathNew) == m_afhHierarchyAlredyCreated.end()){

			Logger::getLogger()->debug("%s - New path requested :%s:", __FUNCTION__, pathNew.c_str());

			sendAFHierarchy(pathNew.c_str());
		}

		if (pathStored.compare("") == 0)
		{
			Logger::getLogger()->debug("%s - New path for the assetName :%s: path :%s:", __FUNCTION__, assetName.c_str(), pathNew.c_str());

			auto item = make_pair(pathNew, prefix);
			m_AssetNamePrefix[assetName].push_back(item);

		} else {
			if (OmfHintHierarchy.compare(pathStored) != 0) {

				Logger::getLogger()->debug("%s - path changed for the assetName :%s: path :%s: previous path :%s:"
										   , __FUNCTION__
										   , assetName.c_str()
										   , pathNew.c_str()
										   , pathStored.c_str());

				deleteAssetAFH(assetName, pathStored);

				auto item = make_pair(pathNew, prefix);
				m_AssetNamePrefix[assetName].clear();
				m_AssetNamePrefix[assetName].push_back(item);
				setPathStored (assetName, pathNew);

				createAssetAFH(assetName, pathNew);

			} else {
				Logger::getLogger()->debug("%s - Same path for the assetName :%s: path :%s:", __FUNCTION__, assetName.c_str(), pathNew.c_str());
			}
			
		}

	}

	// For debug
//	Logger::getLogger()->debug("%s - Hierarchy asset start", __FUNCTION__);
//	for (auto item=m_AssetNamePrefix.begin(); item!=m_AssetNamePrefix.end(); ++item)
//	{
//		auto v = item->second;
//
//		for(auto  arrayItem : v) {
//
//			Logger::getLogger()->debug("%s - Hierarchy asset :%s: hash :%s: path :%s:", __FUNCTION__, item->first.c_str(), arrayItem.first.c_str(), arrayItem.second.c_str());
//		}
//
//	}

	return (ruleMatched);
}

/**
 * Extracts a variable and its elements from a string, the variable will have the shape ${room:unknown}
 *
 * @param strToHandle   Source string from which the variable should be extracted
 * @param variable      Variable found in the form ${room:unknown}
 * @param value         Value of the variable, left part , room in this case ${room:unknown}
 * @param defaultValue  Default value of the variable, right part , unknown in this case ${room:unknown}
 *
 * @return                       True a variable is found in the source string
 */
bool OMF::extractVariable(string &strToHandle, string &variable, string &value, string &defaultValue)
{
	bool found;
	size_t pos1, pos2, pos3;

	found = false;
	variable ="";
	value ="";
	defaultValue ="";

	pos1 = strToHandle.find("${");
	if (pos1 !=std::string::npos)
	{
		pos3 = strToHandle.find("}", pos1);
		pos2 = strToHandle.find(":", pos1);
		if ( (pos2 != std::string::npos) && (pos2 < pos3) )
		{
			value = strToHandle.substr(pos1 + 2, (pos2 - (pos1 + 2) ) );

			pos3 = strToHandle.find("}", pos2);
			if (pos3 != std::string::npos)
			{
				found = true;

				defaultValue = strToHandle.substr(pos2 + 1, (pos3 - (pos2 + 1)));
				variable = strToHandle.substr(pos1, pos3 - pos1 + 1);
			}
		} else {
			Logger::getLogger()->debug("OMF hierarchy hints doesn't have the default value in the metadata reference :%s:", strToHandle.c_str());

			// No default value provided
			if (pos3 != std::string::npos)
			{
				found = true;

				value = strToHandle.substr(pos1 + 2, (pos3 - (pos1 + 2) ) );
				variable = strToHandle.substr(pos1, pos3 - pos1 + 1);
			}
		}
	}

	return(found);
}

/**
 * Evaulate the AF hierarchy provided and expand the variables in the form ${room:unknown}
 *
 * @param reading       Asset reading that should be considered from which extract the metadata values
 * @param AFHierarchy   AF hierarchy containing the variable to be expanded
 *
 * @return              True if variable were found and expanded
 */
std::string OMF::variableValueHandle(const Reading& reading, std::string &AFHierarchy) {

	string AFHierarchyNew;
	string propertyToSearch;
	string propertyValue;
	string propertyDefault;
	string variableValue;
	string propertyName;
	bool found;
	bool foundProperty;

	found = false;
	AFHierarchyNew = AFHierarchy;

	if (AFHierarchyNew.find("${") !=std::string::npos)
	{

		while (extractVariable(AFHierarchyNew, variableValue , propertyToSearch,  propertyDefault))
		{
			auto values = reading.getReadingData();
			foundProperty = false;

			for (auto it = values.begin(); it != values.end(); it++)
			{
				propertyName = (*it)->getName();
				if (propertyName.compare(propertyToSearch) == 0)
				{
					DatapointValue data = (*it)->getData();
					propertyValue = data.toString();
					found = true;
					foundProperty = true;
				}
			}

			if (foundProperty) {

				StringReplaceAll(propertyValue, "\"", "");
				StringReplace(AFHierarchyNew, variableValue, propertyValue);

			} else {
				StringReplaceAll(propertyValue, "\"", "");
				StringReplace(AFHierarchyNew, variableValue, propertyDefault);
			}
		}
	}

	StringReplaceAll(AFHierarchyNew, "//", "/");

	Logger::getLogger()->debug("%s - Variables found :%s: AFHierarchy :%s: AFHierarchyNew :%s: variableValue :%s: propertyToSearch :%s: propertyValue :%s: propertyDefault :%s:"
		,__FUNCTION__
		,found ? "true" : "false"
		,AFHierarchy.c_str()
		,AFHierarchyNew.c_str()
		,variableValue.c_str()
		,propertyToSearch.c_str()
		,propertyValue.c_str()
		,propertyDefault.c_str()
		);

	return (AFHierarchyNew);
}

/**
 * Evaluated the maps containing the Named and Metadata rules to fill the map m_AssetNamePrefix
 * containing for each asset name the related prefix and hierarchy name
 *
 * @param path                   assetName to evaluate
 * @param reading		         reading row from which will be extracted the datapoint for the evaluation of the rules
 */
void OMF::evaluateAFHierarchyRules(const string& assetName, const Reading& reading)
{
	bool ruleMatched = false;
	bool ruleMatchedNames = false;
	bool success;

	string pathInitial;
	string path;
	bool changed;

	// names rules - Check if there are any rules defined or not
	if (!m_AFMapEmptyNames)
	{
		if (! m_NamesRules.empty())
		{

			string pathNamingRules;
			string prefix;
			string AFHierarchyLevel;

			auto it = m_NamesRules.find(assetName);
			if (it != m_NamesRules.end())
			{

				pathInitial = it->second;

				if (pathInitial.at(0) != '/')
				{
					// relative  path
					pathInitial = "/" + m_DefaultAFLocation + "/" + pathInitial;
				}
				path = variableValueHandle(reading, pathInitial);
				path = ApplyPIServerNamingRulesPath(path, &changed);

				if (pathInitial.compare(path) != 0) {

					it->second = path;
				}

				generateAFHierarchyPrefixLevel(path, prefix, AFHierarchyLevel);
				ruleMatched = true;
				ruleMatchedNames = true;

				auto v =  m_AssetNamePrefix[assetName];
				auto item = make_pair(path, prefix);

				if(v.size() == 0 ||  std::find(v.begin(), v.end(), item) == v.end())
				{
					success = sendAFHierarchy(path.c_str());
					m_AssetNamePrefix[assetName].push_back(item);

					Logger::getLogger()->debug(
						"%s - m_NamesRules size :%d: m_AssetNamePrefix size :%d:   vector size :%d: pathInitial :%s: path :%s: stored :%s:"
							,__FUNCTION__
							,m_NamesRules.size()
							,m_AssetNamePrefix.size()
							,v.size()
							,pathInitial.c_str()
							,path.c_str()
							,it->second.c_str());
				} else {
					Logger::getLogger()->debug(
						"%s - m_NamesRules skipped pathInitial :%s: path :%s: stored :%s:"
							,__FUNCTION__
							,pathInitial.c_str()
							,path.c_str()
							,it->second.c_str());
				}
			}
		}
	}

	// Meta rules - Check if there are any rules defined or not
	if (!m_AFMapEmptyMetadata)
	{
		auto values = reading.getReadingData();

		// Metadata Rules - Exist
		if (! m_MetadataRulesExist.empty() )
		{
			string propertyName;
			string prefix;
			string AFHierarchyLevel;

			for (auto it = values.begin(); it != values.end(); it++)
			{
				propertyName = (*it)->getName();
				auto rule = m_MetadataRulesExist.find(propertyName);
				if (rule != m_MetadataRulesExist.end())
				{
					pathInitial = rule->second;;
					if (pathInitial.at(0) != '/')
					{
						pathInitial = "/" + m_DefaultAFLocation + "/" + pathInitial;
					}

					path = variableValueHandle(reading, pathInitial);
					path = ApplyPIServerNamingRulesPath(path, &changed);

					generateAFHierarchyPrefixLevel(path, prefix, AFHierarchyLevel);
					ruleMatched = true;

					auto v =  m_AssetNamePrefix[assetName];
					auto item = make_pair(path, prefix);

					if(v.size() == 0 || std::find(v.begin(), v.end(), item) == v.end())
					{
						success = sendAFHierarchy(path.c_str());
						m_AssetNamePrefix[assetName].push_back(item);

						Logger::getLogger()->debug("%s - m_MetadataRulesExist asset :%s: path added :%s: :%s:" , __FUNCTION__, assetName.c_str(), pathInitial.c_str()  , path.c_str() );
					} else {
						Logger::getLogger()->debug("%s - m_MetadataRulesExist already created asset :%s: path added :%s: :%s:" , __FUNCTION__, assetName.c_str(), pathInitial.c_str()  , path.c_str() );
					}
				}
			}
		}

		// Metadata Rules - NonExist
		if (! m_MetadataRulesNonExist.empty() )
		{
			string propertyName;
			string prefix;
			string AFHierarchyLevel;

			bool found;
			string rule;
			for (auto it = m_MetadataRulesNonExist.begin(); it != m_MetadataRulesNonExist.end(); it++)
			{
				found = false;
				rule = it->first;
				pathInitial = it->second;
				for (auto itL2 = values.begin(); found == false && itL2 != values.end(); itL2++)
				{
					propertyName = (*itL2)->getName();
					if (propertyName.compare(rule) == 0)
					{
						found = true;
					}
				}
				if (!found)
				{
					if (pathInitial.at(0) != '/')
					{
						// relative  path
						pathInitial = "/" +m_DefaultAFLocation + "/" + pathInitial;
					}
					path = variableValueHandle(reading, pathInitial);
					path = ApplyPIServerNamingRulesPath(path, &changed);

					generateAFHierarchyPrefixLevel(path, prefix, AFHierarchyLevel);
					ruleMatched = true;

					auto v =  m_AssetNamePrefix[assetName];
					auto item = make_pair(path, prefix);


					if(v.size() == 0 || std::find(v.begin(), v.end(), item) == v.end())
					{
						success = sendAFHierarchy(path.c_str());
						m_AssetNamePrefix[assetName].push_back(item);

						Logger::getLogger()->debug("%s - m_MetadataRulesNonExist - asset :%s: path added :%s: :%s:" , __FUNCTION__, assetName.c_str(), pathInitial.c_str()  , path.c_str() );
					} else {
						Logger::getLogger()->debug("%s - m_MetadataRulesNonExist -  already created asset :%s: path added :%s: :%s:" , __FUNCTION__, assetName.c_str(), pathInitial.c_str()  , path.c_str() );
					}
				}
			}
		}

		// Metadata Rules - equal
		if ( ! m_MetadataRulesEqual.empty() )
		{
			string propertyName;
			string prefix;
			string AFHierarchyLevel;

			bool found;
			string rule;
			for (auto it = m_MetadataRulesEqual.begin(); it != m_MetadataRulesEqual.end(); it++)
			{
				found = false;
				rule = it->first;
				for (auto itL2 = values.begin(); found == false && itL2 != values.end(); itL2++)
				{
					propertyName = (*itL2)->getName();
					DatapointValue data = (*itL2)->getData();
					string dataValue = data.toString();
					StringStripQuotes(dataValue);
					if (propertyName.compare(rule) == 0)
					{
						for (auto itL3 = it->second.begin(); found == false && itL3 != it->second.end(); itL3++)
						{
							string value = itL3->first;
							StringStripQuotes(value);
							pathInitial = itL3->second;
							if (value.compare(dataValue) == 0)
							{
								found = true;
							}
						}
					}
				}
				if (found)
				{
					if (pathInitial.at(0) != '/')
					{
						// relative  path
						pathInitial = "/" + m_DefaultAFLocation + "/" + pathInitial;
					}
					
					path = variableValueHandle(reading, pathInitial);
					path = ApplyPIServerNamingRulesPath(path, &changed);
					
					generateAFHierarchyPrefixLevel(path, prefix, AFHierarchyLevel);
					ruleMatched = true;

					auto v =  m_AssetNamePrefix[assetName];
					auto item = make_pair(path, prefix);


					if(v.size() == 0 || std::find(v.begin(), v.end(), item) == v.end())
					{
						success = sendAFHierarchy(path.c_str());
						m_AssetNamePrefix[assetName].push_back(item);

						Logger::getLogger()->debug("%s - m_MetadataRulesEqual asset :%s: path added :%s: :%s:" , __FUNCTION__, assetName.c_str(), pathInitial.c_str()  , path.c_str() );
					} else {
						Logger::getLogger()->debug("%s - m_MetadataRulesEqual already created asset :%s: path added :%s: :%s:" , __FUNCTION__, assetName.c_str(), pathInitial.c_str()  , path.c_str() );
					}
					
				}
			}
		}

		// Metadata Rules - Not equal
		if ( ! m_MetadataRulesNotEqual.empty() )
		{
			string propertyName;
			string prefix;
			string AFHierarchyLevel;
			string rule;
			bool NotEqual;

			for (auto it = m_MetadataRulesNotEqual.begin(); it != m_MetadataRulesNotEqual.end(); it++)
			{
				NotEqual = false;
				rule = it->first;
				for (auto itL2 = values.begin(); NotEqual == false && itL2 != values.end(); itL2++)
				{
					propertyName = (*itL2)->getName();

					if (propertyName.compare(rule) == 0)
					{
						DatapointValue data = (*itL2)->getData();
						string dataValue = data.toString();
						StringStripQuotes(dataValue);

						for (auto itL3 = it->second.begin(); NotEqual == false && itL3 != it->second.end(); itL3++)
						{
							string value = itL3->first;
							pathInitial = itL3->second;
							StringStripQuotes(value);

							if (value.compare(dataValue) != 0)
							{
								NotEqual = true;
							}
						}
					}
				}
				if (NotEqual)
				{
					if (pathInitial.at(0) != '/')
					{
						// relative  path
						pathInitial = "/" + m_DefaultAFLocation + "/" + pathInitial;
					}
					path = variableValueHandle(reading, pathInitial);
					path = ApplyPIServerNamingRulesPath(path, &changed);

					generateAFHierarchyPrefixLevel(path, prefix, AFHierarchyLevel);
					ruleMatched = true;

					auto v =  m_AssetNamePrefix[assetName];
					auto item = make_pair(path, prefix);


					if(v.size() == 0 || std::find(v.begin(), v.end(), item) == v.end())
					{
						success = sendAFHierarchy(path.c_str());
						m_AssetNamePrefix[assetName].push_back(item);

						Logger::getLogger()->debug("%s - m_MetadataRulesNotEqual asset :%s: path added :%s: :%s:" , __FUNCTION__, assetName.c_str(), pathInitial.c_str()  , path.c_str() );
					} else {
						Logger::getLogger()->debug("%s - m_MetadataRulesNotEqual already created asset :%s: path added :%s: :%s:" , __FUNCTION__, assetName.c_str(), pathInitial.c_str()  , path.c_str() );
					}
				}
			}
		}
	}

	// If no rules matched se the AF default location
	if ( ! ruleMatched )
	{
		string prefix;
		string AFHierarchyLevel;

		generateAFHierarchyPrefixLevel(m_DefaultAFLocation, prefix, AFHierarchyLevel);

		auto item = make_pair(m_DefaultAFLocation, prefix);
		m_AssetNamePrefix[assetName].push_back(item);
	}

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
			  string& data)
{
	string AFHierarchyPrefix;
	string AFHierarchyLevel;
	string keyComplete;

	// Add the 1st level of AFHierarchy as a prefix to the name in case of PI Web API
	if (m_PIServerEndpoint == ENDPOINT_PIWEB_API)
	{
		retrieveAFHierarchyPrefixAssetName (assetName, AFHierarchyPrefix, AFHierarchyLevel);
		keyComplete = AFHierarchyPrefix + "_" + assetName;
	}
	else
	{
		keyComplete = assetName;
	}

	string AssetTypeTag = to_string(this->getAssetTypeId(assetName)) +
		              "_" + assetName +
		              "_" + tagName;

	// Add the 1st level of AFHierarchy as a prefix to the name in case of PI Web API
	if (m_PIServerEndpoint == ENDPOINT_PIWEB_API)
	{
		AssetTypeTag = "A_" + AFHierarchyPrefix + "_" + AFHierarchyLevel + "_" + AssetTypeTag;
	}
	// Add type-id + '_' + asset_name + '_' + tagName'
	data.append(AssetTypeTag);
}

/**
 * Set the tag ID_XYZ_typename_sensor|typename_measurement using the path in which the asset was created
 *
 * @param assetName    The assetName
 * @param tagName      The tagName to append
 * @param data         The string to append result tag
 */
void OMF::setAssetTypeTagNew(const string& assetName,
						  const string& tagName,
						  string& data)
{
	string path;
	string assetPrefix;
	string AFHierarchyLevel;
	string keyComplete;

	// Add the 1st level of AFHierarchy as a prefix to the name in case of PI Web API
	if (m_PIServerEndpoint == ENDPOINT_PIWEB_API)
	{
		path=getPathOrigStored (assetName);
		generateAFHierarchyPrefixLevel(path, assetPrefix, AFHierarchyLevel);
		keyComplete = assetPrefix + "_" + assetName;
	}
	else
	{
		keyComplete = assetName;
	}

	string AssetTypeTag = to_string(this->getAssetTypeId(assetName)) +
						  "_" + assetName +
						  "_" + tagName;

	// Add the 1st level of AFHierarchy as a prefix to the name in case of PI Web API
	if (m_PIServerEndpoint == ENDPOINT_PIWEB_API)
	{
		AssetTypeTag = "A_" + assetPrefix + "_" + AFHierarchyLevel + "_" + AssetTypeTag;
	}
	// Add type-id + '_' + asset_name + '_' + tagName'
	data.append(AssetTypeTag);
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
bool OMF::handleDataTypes(const string keyComplete, const Reading& row, bool skipSending, OMFHints *hints)
{
	// Create the key for dataTypes sending once
	const string key(skipSending ? (keyComplete) : "");

	// Check whether to create and send Data Types
	bool sendTypes = (skipSending == true) ?
			  // Send if not already sent
			  !OMF::getCreatedTypes(key, row, hints) :
			  // Always send types
			  true;

	// Handle the data types of the current reading
	if (sendTypes && !OMF::sendDataTypes(row, hints))
	{
		// Failure
		return false;
	}

	// We have sent types, we might save this.
	if (skipSending && sendTypes)
	{
		// Save datatypes key
		OMF::setCreatedTypes(row, hints);
	}

	// Success
	return true;
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
 * Set which PIServer component should be used for the communication
 */
void OMF::setPIServerEndpoint(const OMF_ENDPOINT PIServerEndpoint)
{
	m_PIServerEndpoint = PIServerEndpoint;
}

/**
 * Set the first level of hierarchy in Asset Framework in which the assets will be created, PI Web API only.
 */
void OMF::setDefaultAFLocation(const string &DefaultAFLocation)
{
	m_DefaultAFLocation = StringSlashFix(DefaultAFLocation);
}

/**
 * Set the rules to address where assets should be placed in the AF hierarchy.
 * Decodes the JSON and assign to the structures the values about the Names rulues
 *
 */
bool OMF::HandleAFMapNames(Document& JSon)
{
	bool success = true;
	string name;
	string value;

	m_NamesRules.clear();

	Value &JsonNames = JSon["names"];

	for (Value::ConstMemberIterator itr = JsonNames.MemberBegin(); itr != JsonNames.MemberEnd(); ++itr)
	{
		name = itr->name.GetString();
		value = itr->value.GetString();

		if (m_NamesRules.find(name) == m_NamesRules.end())
		{
			Logger::getLogger()->debug("%s - m_NamesRules size :%d: Exist name :%s: value :%s:"
									   	,__FUNCTION__
									   	,m_NamesRules.size()
									   	,name.c_str()
									   	,value.c_str());

			auto newMapValue = make_pair(name, value);
			m_NamesRules.insert(newMapValue);
			m_AFMapEmptyNames = false;
		} else {
			Logger::getLogger()->debug("%s - skipped m_NamesRules size :%d: Exist name :%s: value :%s:"
				,__FUNCTION__
				,m_NamesRules.size()
				,name.c_str()
				,value.c_str());
		}
	}

	return success;
}

/**
 * Set the rules to address where assets should be placed in the AF hierarchy.
 * Decodes the JSON and assign to the structures the values about the Metadata rulues
 *
 */
bool OMF::HandleAFMapMetedata(Document& JSon)
{
	bool success = true;
	string name;
	string value;

	string variable, variableValue, variableDefault;

	Value &JsonMetadata = JSon["metadata"];

	// --- Handling Exist section
	if (JsonMetadata.HasMember("exist"))
	{
		Value &JSonExist = JsonMetadata["exist"];

		for (Value::ConstMemberIterator itr = JSonExist.MemberBegin(); itr != JSonExist.MemberEnd(); ++itr)
		{
			bool changed = false;
			name = itr->name.GetString();
			value = itr->value.GetString();

			Logger::getLogger()->debug("%s - m_MetadataRulesExist :%s: value :%s:", __FUNCTION__, name.c_str(), value.c_str());
			auto newMapValue = make_pair(name,value);

			m_MetadataRulesExist.insert (newMapValue);

			extractVariable(value, variable, variableValue, variableDefault);
			if (! variableDefault.empty()) {

				m_MetadataRulesNonExist.insert (newMapValue);
				m_AFMapEmptyMetadata = false;
			}

			m_AFMapEmptyMetadata = false;
		}
	}

	// --- Handling Non Exist section
	if (JsonMetadata.HasMember("nonexist"))
	{
		Value &JSonNonExist = JsonMetadata["nonexist"];

		for (Value::ConstMemberIterator itr = JSonNonExist.MemberBegin(); itr != JSonNonExist.MemberEnd(); ++itr)
		{
			name = itr->name.GetString();
			value = itr->value.GetString();

			Logger::getLogger()->debug("%s - m_MetadataRulesNonExist :%s: value :%s:", __FUNCTION__, name.c_str(), value.c_str());

			auto newMapValue = make_pair(name,value);

			m_MetadataRulesNonExist.insert (newMapValue);

			m_AFMapEmptyMetadata = false;
		}
	}


	// --- Handling Equal section
	if (JsonMetadata.HasMember("equal"))
	{
		string property;
		string value;
		string path;

		Value &JSonEqual = JsonMetadata["equal"];

		for (Value::ConstMemberIterator itr = JSonEqual.MemberBegin(); itr != JSonEqual.MemberEnd(); ++itr)
		{
			property = itr->name.GetString();

			for (Value::ConstMemberIterator itrL2 = itr->value.MemberBegin(); itrL2 != itr->value.MemberEnd(); ++itrL2)
			{
				value = itrL2->name.GetString();
				path = itrL2->value.GetString();

				Logger::getLogger()->debug("%s - m_MetadataRulesEqual :%s: name :%s: value :%s:", __FUNCTION__, property.c_str() , value.c_str(), path.c_str());

				auto item = make_pair(value,path);
				m_MetadataRulesEqual[property].push_back(item);

				m_AFMapEmptyMetadata = false;
			}
		}
	}
	// --- Handling Not Equal section
	if (JsonMetadata.HasMember("notequal"))
	{
		string property;
		string value;
		string path;

		Value &JSonEqual = JsonMetadata["notequal"];

		for (Value::ConstMemberIterator itr = JSonEqual.MemberBegin(); itr != JSonEqual.MemberEnd(); ++itr)
		{
			property = itr->name.GetString();

			for (Value::ConstMemberIterator itrL2 = itr->value.MemberBegin(); itrL2 != itr->value.MemberEnd(); ++itrL2)
			{
				value = itrL2->name.GetString();
				path = itrL2->value.GetString();

				Logger::getLogger()->debug("%s - m_MetadataRulesNotEqual :%s: name :%s: value :%s:", __FUNCTION__, property.c_str() , value.c_str(), path.c_str());

				auto item = make_pair(value,path);
				m_MetadataRulesNotEqual[property].push_back(item);

				m_AFMapEmptyMetadata = false;
			}
		}
	}
	return success;
}

/**
 * Set the Names and Metadata rules to address where assets should be placed in the AF hierarchy.
 *
 */
bool OMF::setAFMap(const string &AFMap)
{
	bool success = true;
	Document JSon;

	m_AFMapEmptyNames = true;
	m_AFMapEmptyMetadata = true;
	m_AFMap = AFMap;

	ParseResult ok = JSon.Parse(m_AFMap.c_str());
	if (!ok)
	{
		Logger::getLogger()->error("setAFMap - Invalid Asset Framework Map, error :%s:", GetParseError_En(JSon.GetParseError()));
		return false;
	}

	if (JSon.HasMember("names"))
	{
		HandleAFMapNames(JSon);
	}
	if (JSon.HasMember("metadata"))
	{
		HandleAFMapMetedata(JSon);
	}

	return success;
}

/**
 * Set the first level of hierarchy in Asset Framework in which the assets will be created, PI Web API only.
 */
void OMF::setPrefixAFAsset(const string &prefixAFAsset)
{
	m_prefixAFAsset = prefixAFAsset;
}

/**
 * Generate an unique prefix for AF objects
 */
string OMF::generateUniquePrefixId(const string &path)
{
	string prefix;

	std::size_t hierarchyHash = std::hash<std::string>{}(path);
	prefix = std::to_string(hierarchyHash);

	return prefix;
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
	++m_typeId;
}

/**
 * Clear OMF types cache
 */
void OMF::clearCreatedTypes()
{
	if (m_OMFDataTypes)
	{
		m_OMFDataTypes->clear();
	}
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
bool OMF::handleTypeErrors(const string& keyComplete, const Reading& reading, OMFHints *hints)
{
	Logger::getLogger()->debug("handleTypeErrors keyComplete :%s:", keyComplete.c_str());

	bool ret = true;

	string assetName = m_assetName;

	// Reset change type-id indicator
	m_changeTypeId = false;

	// Increment per asset type-id in memory cache:
	// Note: if key is not found the global type-id is incremented
	OMF::incrementAssetTypeId(keyComplete);

	// Clear per asset data (but keep the type-id) if key found
	// or remove all data otherwise
	auto it = m_OMFDataTypes->find(keyComplete);
	if (it != m_OMFDataTypes->end())
	{
		// Clear teh OMF types cache per asset, keep type-id
		OMF::clearCreatedTypes(keyComplete);
	}
	else
	{
		// Remove all cached data, any asset
		OMF::clearCreatedTypes();
	}

	// Force re-send data types with a new type-id
	if (!OMF::handleDataTypes(keyComplete, reading, false, hints))
	{
		Logger::getLogger()->error("Failure re-sending JSON dataType messages "
					   "with new type-id=%d for asset %s",
								   OMF::getAssetTypeId(assetName),
								   assetName.c_str());
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
			    std::map<std::string, Reading*>& dataSuperSet)
{
	// Temporary map for [asset][datapoint] = type
	std::map<string, map<string, string>> readingAllDataPoints;

	// Fetch ALL Reading pointers in the input vector
	// and create a map of [assetName][datapoint1 .. datapointN] = type
	for (vector<Reading *>::const_iterator elem = readings.begin();
						elem != readings.end();
						++elem)
	{
		// Get asset name
		string assetName = ApplyPIServerNamingRulesObj((**elem).getAssetName(), nullptr);

		//string assetName = (**elem).getAssetName();

		// Get all datapoints
		const vector<Datapoint*> data = (**elem).getReadingData();
		// Iterate through datapoints
		for (vector<Datapoint*>::const_iterator it = data.begin();
							it != data.end();
							++it)
		{
			string omfType;
			string datapointName = (*it)->getName();

			if (!isTypeSupported((*it)->getData()))
			{
				omfType = OMF_TYPE_UNSUPPORTED;
				Logger::getLogger()->debug("%s - The type of the datapoint " + assetName + "/" + datapointName + " is unsupported, it will be ignored", __FUNCTION__);
			}
			else
			{
				omfType = omfTypes[((*it)->getData()).getType()];

				// if a OMF hint is applied the type may change
				{
					Reading *reading = *elem;

					// Fetch and parse any OMFHint for this reading
					Datapoint *hintsdp = reading->getDatapoint("OMFHint");
					OMFHints *hints = NULL;

					if (hintsdp && (omfType == OMF_TYPE_FLOAT || omfType == OMF_TYPE_INTEGER))
					{
						hints = new OMFHints(hintsdp->getData().toString());
						const vector<OMFHint *> omfHints = hints->getHints();

						for (auto it = omfHints.cbegin(); it != omfHints.cend(); it++)
						{
							if (typeid(**it) == typeid(OMFIntegerHint))
							{
								omfType = OMF_TYPE_INTEGER;
								break;
							}
						}
					}
				}

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
							Logger::getLogger()->info("Datapoint '" + datapointName + \
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
			else if ((*dp).second.compare(OMF_TYPE_UNSUPPORTED) == 0)
			{
				Logger::getLogger()->debug("%s - The asset '" + assetName + " has a datapoint having an unsupported type, it will be ignored", __FUNCTION__);

				// Avoids to handled PI-Server unsupported datapoint type
				// std::vector<double> vData = {0};
				// DatapointValue vArray(vData);
				// values.push_back(new Datapoint((*dp).first, vArray));
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
/**
 * Extract assetName from error message
 *
 * Currently handled cases
 * (1) $datasource + "." + $id + "_" + $assetName + "_typename_measurement" + ...
 * (2) $id + "measurement_" + $assetName
 *
 * @param    message		OMF error message (JSON)
 * @return   The found assetName if found, or empty string
 */
string OMF::getAssetNameFromError(const char* message)
{
	string assetName;
	Document error;

	error.Parse(message);

	if (!error.HasParseError() &&
	    error.HasMember("source") &&
	    error["source"].IsString())
	{
		string tmp = error["source"].GetString();

		// (1) $datasource + "." + $id + "_" + $assetName + "_typename_measurement" + ...
		size_t found = tmp.find("_typename_measurement");
		if (found != std::string::npos)
		{
			tmp = tmp.substr(0, found);
			found = tmp.find_first_of('.');
			if (found != std::string::npos &&
			    found < tmp.length())
			{
				tmp = tmp.substr(found + 1);
				found = tmp.find_first_of('_');
				if (found != std::string::npos &&
				    found < tmp.length())
				{
					// bug fixed
					//assetName = assetName.substr(found + 1 );
					assetName = tmp.substr(found + 1 );
				}
			}
		}
		else
		{
			// (2) $id + "measurement_" + $assetName
			found = tmp.find_first_of('_');
			if (found != std::string::npos &&
			    found < tmp.length())
			{
				assetName = tmp.substr(found + 1);
			}
		}
	}

	return assetName;
}

/**
 * Return the asset type-id
 *
 * @param assetName	The asset name
 * @return		The found type-id
 *			or the generic value
 */
long OMF::getAssetTypeId(const string& assetName)
{
	long typeId;
	string keyComplete;
	string AFHierarchyPrefix;
	string AFHierarchyLevel;

	// Connector relay / ODS / EDS
	if (m_PIServerEndpoint == ENDPOINT_CR  ||
		m_PIServerEndpoint == ENDPOINT_OCS ||
		m_PIServerEndpoint == ENDPOINT_EDS
		)
	{
		keyComplete = assetName;
	}
	else if (m_PIServerEndpoint == ENDPOINT_PIWEB_API)
	{
		if (getNamingScheme(assetName) == NAMINGSCHEME_CONCISE) {

			keyComplete = assetName;
		} else {
			retrieveAFHierarchyPrefixAssetName(assetName, AFHierarchyPrefix, AFHierarchyLevel);
			keyComplete = AFHierarchyPrefix + "_" + assetName;
		}
	}


	if (!m_OMFDataTypes)
	{
		// Use current value of m_typeId
		typeId = m_typeId;
	}
	else
	{
		auto it = m_OMFDataTypes->find(keyComplete);
		if (it != m_OMFDataTypes->end())
		{
			// Set the type-id of found element
			typeId = ((*it).second).typeId;
		}
		else
		{
			// Use current value of m_typeId
			typeId = m_typeId;
		}
	}

	return typeId;
}

/**
 * Retrieve the naming scheme for the given asset in relation to the end point selected the default naming scheme selected
 * and the naming scheme of the asset itself
 *
 * @param assetName  Asset for quick the naming schema should be retrieved
 * @return           Naming schema of the given asset
 */
long OMF::getNamingScheme(const string& assetName)
{
	long namingScheme;
	string keyComplete;
	string AFHierarchyPrefix;
	string AFHierarchyLevel;

	// Connector relay / ODS / EDS
	if (m_PIServerEndpoint == ENDPOINT_CR  ||
		m_PIServerEndpoint == ENDPOINT_OCS ||
		m_PIServerEndpoint == ENDPOINT_EDS
		)
	{
		keyComplete = assetName;
	}
	else if (m_PIServerEndpoint == ENDPOINT_PIWEB_API)
	{
		retrieveAFHierarchyPrefixAssetName(assetName, AFHierarchyPrefix, AFHierarchyLevel);
		keyComplete = AFHierarchyPrefix + "_" + assetName;
	}


	if (!m_OMFDataTypes)
	{
		// Use current value of m_typeId
		namingScheme = m_NamingScheme;
	}
	else
	{
		auto it = m_OMFDataTypes->find(keyComplete);
		if (it != m_OMFDataTypes->end())
		{
			// Set the type-id of found element
			namingScheme = ((*it).second).namingScheme;
		}
		else
		{
			keyComplete = assetName;

			auto it = m_OMFDataTypes->find(keyComplete);
			if (it != m_OMFDataTypes->end())
			{
				// Set the type-id of found element
				namingScheme = ((*it).second).namingScheme;
			}
			else
			{
				// Use current value of m_typeId
				namingScheme = m_NamingScheme;
			}
		}
	}

	return namingScheme;
}

/**
 * Retrieve the hash for the given asset in relation to the end point selected
 *
 * @param assetName  Asset for quick the hash should be retrieved
 * @return           Hash of the given asset
 */
string OMF::getHashStored(const string& assetName)
{
	string hash;
	string keyComplete;
	string AFHierarchyPrefix;
	string AFHierarchyLevel;

	// Connector relay / ODS / EDS
	if (m_PIServerEndpoint == ENDPOINT_CR  ||
		m_PIServerEndpoint == ENDPOINT_OCS ||
		m_PIServerEndpoint == ENDPOINT_EDS
		)
	{
		keyComplete = assetName;
	}
	else if (m_PIServerEndpoint == ENDPOINT_PIWEB_API)
	{
		if (getNamingScheme(assetName) == NAMINGSCHEME_CONCISE) {

			keyComplete = assetName;
		} else {
			keyComplete = AFHierarchyPrefix + "_" + assetName;
		}
	}


	if (!m_OMFDataTypes)
	{

		hash = "";
	}
	else
	{
		auto it = m_OMFDataTypes->find(keyComplete);
		if (it != m_OMFDataTypes->end())
		{
			// Set the type-id of found element
			hash = ((*it).second).afhHash;
		}
		else
		{
			hash = "";
		}
	}

	return hash;
}

/**
 * Retrieve the current AF hierarchy for the given asset
 *
 * @param assetName  Asset for quick the path should be retrieved
 * @return           Path of the given asset
 */
string OMF::getPathStored(const string& assetName)
{
	string afHierarchy;
	string keyComplete;
	string AFHierarchyPrefix;
	string AFHierarchyLevel;

	// Connector relay / ODS / EDS
	if (m_PIServerEndpoint == ENDPOINT_CR  ||
		m_PIServerEndpoint == ENDPOINT_OCS ||
		m_PIServerEndpoint == ENDPOINT_EDS
		)
	{
		keyComplete = assetName;
	}
	else if (m_PIServerEndpoint == ENDPOINT_PIWEB_API)
	{
		if (getNamingScheme(assetName) == NAMINGSCHEME_CONCISE) {

			keyComplete = assetName;
		} else {
			keyComplete = AFHierarchyPrefix + "_" + assetName;
		}
	}


	if (!m_OMFDataTypes)
	{
		afHierarchy = "";
	}
	else
	{
		auto it = m_OMFDataTypes->find(keyComplete);
		if (it != m_OMFDataTypes->end())
		{
			// Set the type-id of found element
			afHierarchy = ((*it).second).afHierarchy;
		}
		else
		{
			afHierarchy = "";
		}
	}

	return afHierarchy;
}

/**
 * Retrieve the AF hierarchy in which given asset was created
 *
 * @param assetName  Asset for quick the path should be retrieved
 * @return           Path of the given asset
 */
string OMF::getPathOrigStored(const string& assetName)
{
	string afHierarchy;
	string keyComplete;
	string AFHierarchyPrefix;
	string AFHierarchyLevel;

	// Connector relay / ODS / EDS
	if (m_PIServerEndpoint == ENDPOINT_CR  ||
		m_PIServerEndpoint == ENDPOINT_OCS ||
		m_PIServerEndpoint == ENDPOINT_EDS
		)
	{
		keyComplete = assetName;
	}
	else if (m_PIServerEndpoint == ENDPOINT_PIWEB_API)
	{
		if (getNamingScheme(assetName) == NAMINGSCHEME_CONCISE) {

			keyComplete = assetName;
		} else {
			keyComplete = AFHierarchyPrefix + "_" + assetName;
		}
	}


	if (!m_OMFDataTypes)
	{

		afHierarchy = "";
	}
	else
	{
		auto it = m_OMFDataTypes->find(keyComplete);
		if (it != m_OMFDataTypes->end())
		{
			// Set the type-id of found element
			afHierarchy = ((*it).second).afHierarchyOrig;
		}
		else
		{
			afHierarchy = "";
		}
	}

	return afHierarchy;
}

/**
 * Stores the current AF hierarchy for the given asset
 *
 * @param assetName    Asset for quick the path should be retrieved
 * @param afHierarchy  Current AF hierarchy of the asset
 *
 * @return             True if the operation has success
 */
bool OMF::setPathStored(const string& assetName, string &afHierarchy)
{
	bool operationExecuted;
	string keyComplete;
	string AFHierarchyPrefix;
	string AFHierarchyLevel;

	// Connector relay / ODS / EDS
	if (m_PIServerEndpoint == ENDPOINT_CR  ||
		m_PIServerEndpoint == ENDPOINT_OCS ||
		m_PIServerEndpoint == ENDPOINT_EDS
		)
	{
		keyComplete = assetName;
	}
	else if (m_PIServerEndpoint == ENDPOINT_PIWEB_API)
	{
		if (getNamingScheme(assetName) == NAMINGSCHEME_CONCISE) {

			keyComplete = assetName;
		} else {
			keyComplete = AFHierarchyPrefix + "_" + assetName;
		}
	}

	operationExecuted = false;
	if (!m_OMFDataTypes)
	{
		operationExecuted = false;

	}
	else
	{
		auto it = m_OMFDataTypes->find(keyComplete);
		if (it != m_OMFDataTypes->end())
		{
			// Set the type-id of found element
			((*it).second).afHierarchy = afHierarchy;
			operationExecuted = true;
		}
		else
		{
			operationExecuted = false;
		}
	}

	return operationExecuted;
}

/**
 * Increment the type-id for the given asset name
 *
 * If cached data pointer is NULL or asset name is not set
 * the global m_typeId is incremented.
 *
 * @param    keyComplete		The asset name
 *				which type-id sequence
 *				has to be incremented.
 */
void OMF::incrementAssetTypeId(const std::string& keyComplete)
{
	long typeId;
	if (!m_OMFDataTypes)
        {
		// Increment current value of m_typeId
		OMF::incrementTypeId();
        }
	else
	{
		auto it = m_OMFDataTypes->find(keyComplete);
		if (it != m_OMFDataTypes->end())
		{
			// Increment value of found type-id
			++((*it).second).typeId;
		}
		else
		{
			// Increment current value of m_typeId
			OMF::incrementTypeId();
		}
	}
}

/**
 * Increment the type-id for the given asset name
 *
 * If cached data pointer is NULL or asset name is not set
 * the global m_typeId is incremented.
 *
 * @param    keyComplete		The asset name
 *				                which type-id sequence
 *				                has to be incremented.
 */
void OMF::incrementAssetTypeIdOnly(const std::string& keyComplete)
{
	long typeId;
	if (m_OMFDataTypes)
	{
		auto it = m_OMFDataTypes->find(keyComplete);
		if (it != m_OMFDataTypes->end())
		{
			// Increment value of found type-id
			++((*it).second).typeId;
		}
	}
}


/**
 * Generate a 64 bit number containing  a set of counts,
 * number of datapoint in an asset and the number of datapoint of each type we support.
 *
 */
unsigned long OMF::calcTypeShort(const Reading& row)
{
	t_typeCount typeCount;

	int type;

	const vector<Datapoint*> data = row.getReadingData();
	for (vector<Datapoint*>::const_iterator it = data.begin();
		 (it != data.end() &&
		  isTypeSupported((*it)->getData()));
		 ++it)
	{
		string dpName = (*it)->getName();

		if (!isTypeSupported((*it)->getData()))
		{
			continue;
		}

		if (dpName.compare(OMF_HINT) == 0)
		{
			// We never include OMF hints in the data we send to PI
			continue;
		}

		type = ((*it)->getData()).getType();

		// Integer is handled as float in the OMF integration
		if (type == DatapointValue::dataTagType::T_INTEGER)
		{
			typeCount.cnt.tFloat++;
		}

		if (type == DatapointValue::dataTagType::T_FLOAT)
		{
			typeCount.cnt.tFloat++;
		}

		if (type == DatapointValue::dataTagType::T_STRING)
		{
			typeCount.cnt.tString++;

		}
		typeCount.cnt.tTotal++;

	}

	return typeCount.valueLong;
}

/**
 * Add the reading asset namekey into a map
 * That key is checked by getCreatedTypes in order
 * to send dataTypes only once
 *
 * @param row    The reading data row
 * @return       True, false if map pointer is NULL
 */
bool OMF::setCreatedTypes(const Reading& row, OMFHints *hints)
{
	string types;
	string keyComplete;
	string assetName;
	string AFHierarchyPrefix;
	string AFHierarchy;

	if (!m_OMFDataTypes)
	{
		return false;
	}

	assetName = m_assetName;
	retrieveAFHierarchyFullPrefixAssetName(assetName, AFHierarchyPrefix, AFHierarchy);

	// Connector relay / ODS / EDS
	if (m_PIServerEndpoint == ENDPOINT_CR  ||
		m_PIServerEndpoint == ENDPOINT_OCS ||
		m_PIServerEndpoint == ENDPOINT_EDS
		)
	{
		keyComplete = m_assetName;
	}
	else if (m_PIServerEndpoint == ENDPOINT_PIWEB_API)
	{
		if (getNamingScheme(assetName) == NAMINGSCHEME_CONCISE) {

			keyComplete = assetName;
		} else {
			keyComplete = AFHierarchyPrefix + "_" + assetName;
		}
	}

	// We may need to add the hint to the key if we have a TypeName key
	if (hints)
	{
		const vector<OMFHint *> omfHints = hints->getHints();
		for (auto it = omfHints.cbegin(); it != omfHints.cend(); it++)
		{
			if (typeid(**it) == typeid(OMFTypeNameHint))
			{
					Logger::getLogger()->info("Using OMF TypeName hint: %s", (*it)->getHint().c_str());
				keyComplete.append("_" + (*it)->getHint());
				break;
			}
		}
	}


	long typeId = OMF::getAssetTypeId(keyComplete);
	const vector<Datapoint*> data = row.getReadingData();
	types.append("{");
	bool first = true;
	for (vector<Datapoint*>::const_iterator it = data.begin();
						(it != data.end() &&
						 isTypeSupported((*it)->getData()));
						++it)
	{
		string dpName = (*it)->getName();
		if (dpName.compare(OMF_HINT) == 0)
		{
			// We never include OMF hints in the data we send to PI
			continue;
		}
		if (!first)
		{
			types.append(", ");
		}
		else
		{
			first = false;
		}

		string omfType;
		if (!isTypeSupported((*it)->getData()))
		{
			omfType = OMF_TYPE_UNSUPPORTED;
			continue;
		}
		else
		{
			omfType = omfTypes[((*it)->getData()).getType()];
		}

		string format = OMF::getFormatType(omfType);
		if (hints && (omfType == OMF_TYPE_FLOAT || omfType == OMF_TYPE_INTEGER))
		{
			const vector<OMFHint *> omfHints = hints->getHints(dpName);
			for (auto it = omfHints.cbegin(); it != omfHints.cend(); it++)
			{
				if (typeid(**it) == typeid(OMFNumberHint))
				{
					format = (*it)->getHint();
					break;
				}
				if (typeid(**it) == typeid(OMFIntegerHint))
				{
					omfType = OMF_TYPE_INTEGER;
					format = (*it)->getHint();
					break;
				}
			}
		}

		// Add datapoint Name
		types.append("\"" + dpName + "\"");
		types.append(": {\"type\": \"");
		// Add datapoint Type
		types.append(omfType);

		// Applies a format if it is defined
		if (!format.empty())
		{
			types.append("\", \"format\": \"");
			types.append(format);
		}

		types.append("\"}");
	}
	types.append("}");

	if (m_OMFDataTypes->find(keyComplete) == m_OMFDataTypes->end())
	{
		// New entry
		OMFDataTypes newData;
		// Start from default as we don't have anything in the cache
		newData.typeId = m_typeId;

		newData.types = types;
		(*m_OMFDataTypes)[keyComplete] = newData;
	}
	else
	{
		// Just update dataTypes and keep the typeId
		(*m_OMFDataTypes)[keyComplete].types = types;
	}

	(*m_OMFDataTypes)[keyComplete].typesShort = calcTypeShort(row);
	(*m_OMFDataTypes)[keyComplete].hintChkSum = hints ? hints->getChecksum() : 0;

	(*m_OMFDataTypes)[keyComplete].namingScheme     = m_NamingScheme;
	(*m_OMFDataTypes)[keyComplete].afhHash          = AFHierarchyPrefix;
	(*m_OMFDataTypes)[keyComplete].afHierarchy      = AFHierarchy;
	(*m_OMFDataTypes)[keyComplete].afHierarchyOrig  = AFHierarchy;

	Logger::getLogger()->debug("%s - keyComplete :%s: m_NamingScheme :%ld: AFHierarchyPrefix :%s: AFHierarchy :%s: "
				, __FUNCTION__
				, keyComplete.c_str()
				, m_NamingScheme
				, AFHierarchyPrefix.c_str()
				, AFHierarchy.c_str() );

	return true;
}

/**
 * Set a new value for global type-id
 *
 * new value is the maximum value of
 * type-id among all asset datatypes
 * or
 * the current value of m_typeId
 */
void OMF::setTypeId()
{
	long maxId = m_typeId;
	for (auto it = m_OMFDataTypes->begin();
		  it != m_OMFDataTypes->end();
		  ++it)
	{
		if ((*it).second.typeId > maxId)
		{
			maxId = (*it).second.typeId;
		}
	}
	m_typeId = maxId;
}

/**
 * Clear OMF types cache for given asset name
 * but keep the type-id
 */
void OMF::clearCreatedTypes(const string& keyComplete)
{
	if (m_OMFDataTypes)
	{
		auto it = m_OMFDataTypes->find(keyComplete);
		if (it != m_OMFDataTypes->end())
		{
			// Just clear data types
			(*it).second.types = "";
		}
	}
}

/**
 * Check the key (assetName) is set and not empty
 * in the per asset data types cache.
 *
 * @param keyComplete    The data type key (assetName) from the Reading row
 * @return       True is the key exists and data value is not empty:
 *		 this means the dataTypes were already sent
 *		 Found key with empty value means the data types
 *		 must be sent again with the new type-id.
 *               Return false if the key is not found or found but empty.
 */
bool OMF::getCreatedTypes(const string& keyComplete, const Reading& row, OMFHints *hints)
{
	unsigned long typesDefinition;
	bool ret = false;
	bool found = false;

	t_typeCount typeStored;
	t_typeCount typeNew;

	if (!m_OMFDataTypes)
	{
		ret = false;
	}
	else
	{
		auto it = m_OMFDataTypes->find(keyComplete);
		if (it != m_OMFDataTypes->end())
		{
			OMFDataTypes& type = it->second;
			ret = ! type.types.empty();
			if (ret)
			{
				// Considers empty also the case "{}"
				if (type.types.compare("{}") == 0)
				{
					ret = false;
				}
				else
				{
					// The Connector Relay recreates the type only when an error is received from the PI-Server
					// not in advance
					if (m_PIServerEndpoint != ENDPOINT_CR)
					{
						if (hints && type.hintChkSum != hints->getChecksum())
						{
							ret = false;
						}
						else
						{
							// Check if the defined type has changed respect the superset type
							Reading* datatypeStructure = NULL;

							auto itSuper = m_SuperSetDataPoints.find(m_assetName);

							if (itSuper != m_SuperSetDataPoints.end())
							{
								datatypeStructure = (*itSuper).second;

								// Check if the types are changed
								typeStored.valueLong = type.typesShort;
								typeNew.valueLong = calcTypeShort(*datatypeStructure);

								if (typeNew.cnt.tTotal  > typeStored.cnt.tTotal ||
									typeNew.cnt.tFloat  > typeStored.cnt.tFloat ||
									typeNew.cnt.tString > typeStored.cnt.tString
									)
								{
									ret = false;
								}
							}
						}
					}
				}
			}
		}
	}
	return ret;
}

/**
 * Check whether input Datapoint type is supported by OMF class
 *
 * @param    dataPoint		Input data
 * @return			True is fupported, false otherwise
 */ 

static bool isTypeSupported(DatapointValue& dataPoint)
{
	if (dataPoint.getType() == DatapointValue::DatapointTag::T_FLOAT_ARRAY ||
	    dataPoint.getType() == DatapointValue::DatapointTag::T_DP_DICT ||
	    dataPoint.getType() == DatapointValue::DatapointTag::T_DP_LIST)
	{
		return false;
	}
	else
	{
		return true;
	}
}

/**
 * Check a PI Server name and returns the proper name to use following the naming rules
 *
 * Invalid chars: Control characters plus: * ? ; { } [ ] | \ ` ' "
 *
 * @param    objName  The object name to verify
 * @param    changed  if not null, it is set to true if a change occur
 * @return			  Object name following the PI Server naming rules
 */
std::string OMF::ApplyPIServerNamingRulesInvalidChars(const std::string &objName, bool *changed)
{
	std::string nameFixed;

	if (changed)
		*changed = false;

	nameFixed = objName;

	for (size_t i = 0; i < nameFixed.length(); i++)
	{
		if (
			nameFixed[i] == '*'  ||
			nameFixed[i] == '?'  ||
			nameFixed[i] == ';'  ||
			nameFixed[i] == '{'  ||
			nameFixed[i] == '}'  ||
			nameFixed[i] == '['  ||
			nameFixed[i] == ']'  ||
			nameFixed[i] == '|'  ||
			nameFixed[i] == '\\' ||
			nameFixed[i] == '`'  ||
			nameFixed[i] == '\'' ||
			nameFixed[i] == '\"' ||
			iscntrl(nameFixed[i])
			)
		{
			nameFixed.replace(i, 1, "_");

			if (changed)
				*changed = true;
		}

	}

	return (nameFixed);
}

/**
 * Check a PI Server object name and returns the proper name to use following the naming rules:
 *
 * - Blank names are not permitted, substituted with '_'
 * - Trailing spaces are removed
 * - Maximum name length is 200 characters.
 * - Valid chars
 * - Names cannot begin with '__', These are reserved for system use, substituted with single '_'
 *
 * Note: Names on PI-Server side are not case sensitive
 *
 * @param    objName  The object name to verify
 * @param    changed  if not null, it is set to true if a change occur
 * @return			  Object name following the PI Server naming rules
 */
std::string OMF::ApplyPIServerNamingRulesObj(const std::string &objName, bool *changed)
{
	std::string nameFixed;

	if (changed)
		*changed = false;

	nameFixed = StringTrim(objName);

	Logger::getLogger()->debug("%s - original :%s: trimmed :%s:", __FUNCTION__, objName.c_str(), nameFixed.c_str());

	if (nameFixed.empty ()) {

		Logger::getLogger()->debug("%s - object name empty", __FUNCTION__);

		nameFixed = "_";
		if (changed)
			*changed = true;

	} else {
		if (nameFixed.length() > 201) {

			nameFixed = nameFixed.substr(0, 200);
			if (changed)
				*changed = true;

			Logger::getLogger()->warn("%s - object name too long, truncated to :%s: ", __FUNCTION__, nameFixed.c_str() );
		}
	}

	nameFixed = ApplyPIServerNamingRulesInvalidChars(nameFixed, changed);

	/// Names cannot begin with '__'. These are reserved for system use.
	if (
		nameFixed[0] == '_'  &&
		nameFixed[1] == '_'
		)
	{
		nameFixed.erase(0, 1);
		if (changed)
			*changed = true;
	}

	Logger::getLogger()->debug("%s - final :%s: ", __FUNCTION__, nameFixed.c_str());

	return (nameFixed);
}


/**
 * Check a PI Server path name and returns the proper name to use following the naming rules:
 *
 * - Blank names are not permitted, substituted with '_'
 * - Trailing spaces are removed
 * - Maximum name length is 200 characters.
 * - Valid chars
 * - Names cannot begin with '__', These are reserved for system use, substituted with single '_'
 *
 * Names on PI-Server side are not case sensitive
 *
 * @param    objName  The object name to verify
 * @param    changed  if not null, it is set to true if a change occur
 * @return			  Object name following the PI Server naming rules
 */
std::string OMF::ApplyPIServerNamingRulesPath(const std::string &objName, bool *changed)
{
	std::string nameFixed;

	if (changed)
		*changed = false;

	nameFixed = StringTrim(objName);

	Logger::getLogger()->debug("%s - original :%s: trimmed :%s:", __FUNCTION__, objName.c_str(), nameFixed.c_str());

	if (nameFixed.empty ()) {

		Logger::getLogger()->debug("%s - path empty", __FUNCTION__);
		nameFixed = "_";
		if (changed)
			*changed = true;

	} else {
		if (nameFixed.length() > 201) {

			nameFixed = nameFixed.substr(0, 200);
			if (changed)
				*changed = true;

			Logger::getLogger()->warn("%s - path too long, truncated to :%s: ", __FUNCTION__, nameFixed.c_str() );
		}
	}

	nameFixed = ApplyPIServerNamingRulesInvalidChars(nameFixed, changed);

	/// Names cannot begin with '__'. These are reserved for system use.
	if (
		nameFixed[0] == '_' &&
		nameFixed[1] == '_'
		)
	{
		nameFixed.erase(0, 1);
		if (changed)
			*changed = true;
	}

	if (nameFixed.find("/__") != string::npos)
	{
		StringReplaceAll(nameFixed,"/__","/_");
		if (changed)
			*changed = true;

	}

	Logger::getLogger()->debug("%s - final :%s: ", __FUNCTION__, nameFixed.c_str());

	return (nameFixed);
}

