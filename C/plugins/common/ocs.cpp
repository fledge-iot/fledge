/*
 * Fledge OSI Soft OCS integration.
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

#include <ocs.h>
#include <logger.h>
#include <simple_https.h>
#include <rapidjson/document.h>
#include "rapidjson/error/en.h"

using namespace std;
using namespace rapidjson;

OCS::OCS()
{
}

// Destructor
OCS::~OCS()
{
}

// FIXME_I:

std::string OCS::extractToken(const string& response)
{
	Document JSon;
	string token;

	ParseResult ok = JSon.Parse(response.c_str());
	if (!ok)
	{
		Logger::getLogger()->error("OCS token extract, invalid json - HTTP response :%s:", response.c_str());
	}

	if (JSon.HasMember("access_token"))
	{
		token = JSon["access_token"].GetString();
	}

	return(token);
}

// FIXME_I:
std::string OCS::retrieveToken(const string& clientId, const string& clientSecret)
{
	string token;
	string response;
	string payload;

	HttpSender *endPoint;
	vector<pair<string, string>> header;
	int httpCode;

	endPoint = new SimpleHttps(OCS_HOST,
							   TIMEOUT_CONNECT,
							   TIMEOUT_REQUEST,
							   RETRY_SLEEP_TIME,
							   MAX_RETRY);

	header.push_back( std::make_pair("Content-Type", "application/x-www-form-urlencoded"));
	header.push_back( std::make_pair("Accept", " text/plain"));

	payload =  "grant_type=client_credentials&client_id=" + clientId + "&client_secret=" + clientSecret;

	// Anonymous auth
	string authMethod = "a";
	endPoint->setAuthMethod (authMethod);

	try
	{
		httpCode = endPoint->sendRequest("POST",
										 URL_RETRIEVE_TOKEN,
										 header,
										 payload);

		response = endPoint->getHTTPResponse();

		if (httpCode >= 200 && httpCode <= 399)
		{
			token = extractToken(response);
			Logger::getLogger()->debug("OCS authentication token :%s:" ,token.c_str() );
		}
		else
		{
			Logger::getLogger()->warn("Error in retriving the authentication token from OCS - http :%d: :%s: ", httpCode, response.c_str());
		}

	}
	catch (exception &ex)
	{
		Logger::getLogger()->warn("Error in retriving the authentication token from OCS - error :%s: ", ex.what());
	}

	delete endPoint;

	return token;
}