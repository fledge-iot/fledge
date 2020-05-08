/*
 * Fledge OSI Soft PIWebAPI integration.
 *
 * Copyright (c) 2020 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Stefano Simonelli
 */

#include <string>
#include <vector>
#include <utility>

#include <piwebapi.h>
#include <string_utils.h>
#include <logger.h>
#include <simple_https.h>
#include <string_utils.h>

#include <rapidjson/document.h>
#include "rapidjson/error/en.h"

using namespace std;
using namespace rapidjson;

PIWebAPI::PIWebAPI()
{
}

// Destructor
PIWebAPI::~PIWebAPI()
{
}

/**
 * Extracts the PIWebAPI version from the JSON returned by the PIWebAPI api
 */
std::string PIWebAPI::ExtractVersion(const string& response)
{
	Document JSon;
	string version;
	string responseFixed;
	ParseResult ok;

	// TODO: at the current stage a non JSON is returned, so we fixed the format
	ok = JSon.Parse(response.c_str());
	if (!ok)
	{
		responseFixed = "{\"" + response;
		StringStripCRLF(responseFixed);
	}
	else
	{
		responseFixed = response;
	}

	ok = JSon.Parse(responseFixed.c_str());
	if (!ok)
	{
		Logger::getLogger()->error("PIWebAPI version extract, invalid json - HTTP response :%s:", response.c_str());
	}
	else
	{
		if (JSon.HasMember("ProductTitle"))
		{
			version = JSon["ProductTitle"].GetString();
		}
		if (JSon.HasMember("ProductVersion"))
		{
			version = version + "-" + JSon["ProductVersion"].GetString();
		}

	}

	return(version);
}


/**
 * Calls the PIWebAPI api to retrieve the version
 */
std::string PIWebAPI::GetVersion(const string& host)
{
	string version;
	string response;
	string payload;

	HttpSender *endPoint;
	vector<pair<string, string>> header;
	int httpCode;

	endPoint = new SimpleHttps(host,
							   TIMEOUT_CONNECT,
							   TIMEOUT_REQUEST,
							   RETRY_SLEEP_TIME,
							   MAX_RETRY);

	// HTTP header
	header.push_back( std::make_pair("Content-Type", "application/json"));
	header.push_back( std::make_pair("Accept", "application/json"));

	// HTTP payload
	payload =  "";

	// Anonymous auth
	string authMethod = "a";
	endPoint->setAuthMethod (authMethod);

	try
	{
		// FIXME_I:
//		httpCode = endPoint->sendRequest("GET",
//										 URL_GET_VERSION,
//										 header,
//										 payload);
//
//		response = endPoint->getHTTPResponse();
		httpCode = 200;
		response = "DBG version";

		if (httpCode >= 200 && httpCode <= 399)
		{
			// FIXME_I:
			//version = ExtractVersion(response);
			version =response;
		}
		else
		{
			Logger::getLogger()->warn("Error in retrieving the PIWebAPI version - http :%d: :%s: ", httpCode, response.c_str());
		}
	}
	catch (exception &ex)
	{
		Logger::getLogger()->warn("Error in retrieving the PIWebAPI version - error :%s: ", ex.what());
	}

	delete endPoint;

	return version;
}