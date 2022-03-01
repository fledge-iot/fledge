/*
 * Fledge bearer token utilities
 *
 * Copyright (c) 2022 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Massimiliano Pinto
 */

#include "bearer_token.h"

using namespace std;
using HttpServer = SimpleWeb::Server<SimpleWeb::HTTP>;

/**
 * Extract access bearer token from request object
 *
 * @param request	HTTP request object
 * @return		Access token as std::string
 *			Empty string if no bearer token
 */
string getAccessBearerToken(shared_ptr<HttpServer::Request> request)
{
	string bearer_token;

        for(auto &field : request->header)
        {
                if (field.first == AUTH_HEADER)
                {
                        std::size_t pos = field.second.rfind(BEARER_SCHEMA);
                        if (pos != string::npos)
                        {
                                pos += strlen(BEARER_SCHEMA);
                                bearer_token = field.second.substr(pos);
                        }
                }
        }

        return bearer_token;
}

/**
 * Split JWT token (yyyy.wwww.zzzz) components into a vector of strings
 *
 * @param    s          The JWT bearer token string
 * @param    delim      The JWT bearer token delimiter char
 * @return              A vector of strings with token components
 */
vector<string> JWTTokenSplit(const string &s, char delim)
{
	stringstream ss(s);
	string item;
	// Output array
	vector<string> elems;

	while (std::getline(ss, item, delim)) {
		elems.push_back(item);
	}

	return elems;
}
