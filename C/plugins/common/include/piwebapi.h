#ifndef _PIWEBAPI_H
#define _PIWEBAPI_H
/*
 * Fledge OSIsoft PI Web API integration.
 *
 * Copyright (c) 2020-2022 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Stefano Simonelli
 */

#include <string>

using namespace std;

#define TIMEOUT_CONNECT   10
#define TIMEOUT_REQUEST   10
#define RETRY_SLEEP_TIME  1
#define MAX_RETRY         3

#define URL_GET_VERSION "/piwebapi/system"

/**
 * The PIWebAPI class.
 */
class PIWebAPI
{
	public:
		PIWebAPI();


		// Destructor
		~PIWebAPI();

		void    setAuthMethod          (std::string& authMethod)           {m_authMethod = authMethod; }
		void    setAuthBasicCredentials(std::string& authBasicCredentials) {m_authBasicCredentials = authBasicCredentials; }

		int     GetVersion(const string& host, string &version, bool logMessage = true);
		string  errorMessageHandler(const string& msg);

	private:
		string  ExtractVersion(const string& response);
		string  extractSection(const string& msg, const string& toSearch);
		string  extractMessageFromJSon(const string& json);

		string  m_authMethod;             // Authentication method to be used
		string  m_authBasicCredentials;   // Credentials is the base64 encoding of id and password joined by a single colon (:)

		// Substitute a message with a different one
		const vector<pair<string, string>> PIWEB_ERRORS = {
			//   original message       New one
			{"Noroutetohost",    "The PI Web API server is not reachable, verify the network reachability"},
			{"No route to host", "The PI Web API server is not reachable, verify the network reachability"},
		};


};
#endif
