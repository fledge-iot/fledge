#ifndef _OCS_H
#define _OCS_H
/*
 * Fledge OSIsoft ADH and OCS integration.
 *
 * Copyright (c) 2020-2025 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Stefano Simonelli
 */

#include <string>
#include <chrono>

using namespace std;

#define TIMEOUT_CONNECT   10
#define TIMEOUT_REQUEST   10
#define RETRY_SLEEP_TIME  1

#define URL_RETRIEVE_TOKEN "/identity/connect/token"

#define PAYLOAD_RETRIEVE_TOKEN "grant_type=client_credentials&client_id=CLIENT_ID_PLACEHOLDER&client_secret=CLIENT_SECRET_ID_PLACEHOLDER"

/**
 * The OCS class.
 */
class OCS
{
	public:
		OCS(const std::string &authorizationUrl);

		// Destructor
		~OCS();

		std::string	OCSRetrieveAuthToken(const string& clientId, const string& clientSecret, bool logMessage = true);
		int  retrieveToken(const string& clientId, const string& clientSecret, bool logMessage = true);
		void  extractToken(const string& response);
	private:
		std::string m_token;
		std::string m_authUrl;
		unsigned int m_expiresIn;
		std::chrono::steady_clock::time_point m_nextAuthentication;
};
#endif
