#ifndef _PIWEBAPI_H
#define _PIWEBAPI_H
/*
 * Fledge OSI Soft PI Web API integration.
 *
 * Copyright (c) 2020 Dianomic Systems
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

		string  GetVersion(const string& host);

	private:
		string  ExtractVersion(const string& response);

		string  m_authMethod;             // Authentication method to be used
		string  m_authBasicCredentials;   // Credentials is the base64 encoding of id and password joined by a single colon (:)

};
#endif
