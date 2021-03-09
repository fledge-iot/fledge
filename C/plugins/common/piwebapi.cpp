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

//# FIXME_I:
#include <stdlib.h>
#include <string.h>
#include <status_code.hpp>
#include <tmp_log.hpp>

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

	// Set requested authentication
	endPoint->setAuthMethod          (m_authMethod);
	endPoint->setAuthBasicCredentials(m_authBasicCredentials);

	try
	{
		httpCode = endPoint->sendRequest("GET",
										 URL_GET_VERSION,
										 header,
										 payload);

		response = endPoint->getHTTPResponse();

		if (httpCode >= 200 && httpCode <= 399)
		{
			version = ExtractVersion(response);
		}
		else
		{
			string errorMsg;
			errorMsg = errorMessageHandler(response);

			Logger::getLogger()->warn("Error in retrieving the PIWebAPI version, :%d: %s ", httpCode, errorMsg.c_str());
		}
	}
	catch (exception &ex)
	{
		string errorMsg;
		errorMsg = errorMessageHandler(ex.what());

		Logger::getLogger()->warn("Error in retrieving the PIWebAPI version, %s ", errorMsg.c_str());
	}

	delete endPoint;

	return version;
}

string PIWebAPI::extractSection(const string& msg, const string& toSearch) {

	string::size_type pos, pos1, pos2;
	string section;

	pos = msg.find (toSearch);
	if (pos != string::npos )
	{
		pos1 = msg.find ("|",pos);
		pos2 = msg.find ("|",pos1+1);
		if (pos2 != string::npos ) {

			section = msg.substr(pos1 +1, pos2 - pos1 -1);
		}
	}
	return (section);
}

string PIWebAPI::extractMessageFromJSon(const string& json)
{
	Document JSon;
	ParseResult ok;
	string::size_type pos;

	string  msgFinal, msgFixed;
	string msgMessage, msgName, msgValue;

	msgFixed = extractSection(json, "HTTP error |");
	if (msgFixed.empty())
		msgFixed = json;

	ok = JSon.Parse(msgFixed.c_str());
	if (!ok)
	{
		// removes bad characters if present in the error message
		char badChars[4];
		badChars[0]='\357';
		badChars[1]='\273';
		badChars[2]='\277';
		badChars[3]=0;

		pos = msgFixed.find (badChars);
		if (pos != string::npos )
		{
			msgFixed.erase ( pos, strlen(badChars) );
		}
	}

	ok = JSon.Parse(msgFixed.c_str());
	if (ok)
	{
		if (JSon.HasMember("Messages"))
		{
			Value &messages = JSon["Messages"];
			if (messages.IsArray())
			{
				long messageId;
				for (Value::ConstValueIterator itr = messages.Begin(); itr != messages.End(); ++itr)
				{
					messageId = (*itr)["MessageIndex"].GetInt64();

					if ((*itr).HasMember("Events"))
					{
						const Value &messageEvents = (*itr)["Events"];
						if (messageEvents.IsArray())
						{
							Value::ConstValueIterator itrEvents = messageEvents.Begin();

							const Value &messageInfo = (*itrEvents)["EventInfo"];
							msgMessage = messageInfo["Message"].GetString();

							const Value &parameters = messageInfo["Parameters"];
							if (parameters.IsArray())
							{

								for (Value::ConstValueIterator itrParameters = parameters.Begin(); itrParameters != parameters.End(); ++itrParameters)
								{
									if (! msgValue.empty())
										msgValue += " ";

									msgName = (*itrParameters)["Name"].GetString();
									msgValue += (*itrParameters)["Value"].GetString();
								}

								msgFinal = msgMessage + " " + msgValue;
								break;

							} else {
								Logger::getLogger()->warn("xxx %s - PI Web API errors handling expects to received Parameters as an JSON array", __FUNCTION__);
							}
						}
					} else {
						Logger::getLogger()->warn("xxx %s - PI Web API errors handling expects to received Events as an JSON array", __FUNCTION__);
					}

				}

			} else {
				Logger::getLogger()->warn("xxx %s - PI Web API errors handling expects to received Messages as an JSON array", __FUNCTION__);
			}
		}
	}

	return (msgFinal);
}
// FIXME_I:
string PIWebAPI::errorMessageHandler(const string& msg)
{
	Document JSon;
	ParseResult ok;



	string msgTrimmed, msgSub, msgHttp, msgJson, finalMsg, msgFixed, messages, tmpMsg;
	string httpCode;
	int  httpCodeN;

	//# FIXME_I
	Logger::getLogger()->setMinLevel("debug");
	Logger::getLogger()->debug("xxx %s - msg :%s:", __FUNCTION__, msg.c_str());


	//# FIXME_I:
	char tmp_buffer[500000];
	snprintf (tmp_buffer,500000, "DBG : errorMsg  |%s| " ,msg.c_str());
	tmpLogger (tmp_buffer);

	msgTrimmed = StringStripWhiteSpacesExtra(msg);

	// Handles error message substitution
	for(auto &errorMsg : PIWEB_ERRORS) {

		if (msgTrimmed.find(errorMsg.first) != std::string::npos)
		{
			msgSub = errorMsg.second;
		}
	}

	// Handles HTTP error code recognition
	httpCode = extractSection(msgTrimmed, "HTTP code |");
	if (! httpCode.empty()) {

			SimpleWeb::StatusCode code;

			httpCodeN = atoi(httpCode.c_str());
			code = (SimpleWeb::StatusCode) httpCodeN;

			msgHttp = SimpleWeb::status_code(code);

	}

	// Handles error in JSON format returned by the PI Web API
	msgJson = extractMessageFromJSon (msgTrimmed);


	// Define the final message
	finalMsg = msg;
	if (!msgSub.empty())
		finalMsg = msgSub;

	if (!msgHttp.empty())
		finalMsg = msgHttp;

	if (!msgJson.empty())
		finalMsg = msgJson;


	//# FIXME_I
	Logger::getLogger()->debug("xxx %s - finalMsg :%s:", __FUNCTION__, finalMsg.c_str());
	Logger::getLogger()->setMinLevel("warning");


	return(finalMsg);
}
