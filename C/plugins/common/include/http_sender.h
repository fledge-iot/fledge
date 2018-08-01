#ifndef _HTTP_SENDER_H
#define _HTTP_SENDER_H
/*
 * FogLAMP HTTP Sender wrapper.
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Massimiliano Pinto
 */

#include <string>
#include <vector>

#define HTTP_SENDER_USER_AGENT     "FogLAMP http sender"
#define HTTP_SENDER_DEFAULT_METHOD "GET"
#define HTTP_SENDER_DEFAULT_PATH   "/"

class HttpSender
{
	public:
		/**
		 * Constructor:
		 */
		HttpSender();

		// Destructor
		virtual ~HttpSender();

		/**
		 * HTTP(S) request: pass method and path, HTTP headers and POST/PUT payload.
		 */
		virtual int sendRequest(const std::string& method = std::string(HTTP_SENDER_DEFAULT_METHOD),
				const std::string& path = std::string(HTTP_SENDER_DEFAULT_PATH),
				const std::vector<std::pair<std::string, std::string>>& headers = {},
				const std::string& payload = std::string()) = 0;

                virtual std::string getHostPort() = 0;
};

#endif
