#ifndef _BEARER_TOKEN_H
#define _BEARER_TOKEN_H
/*
 * Fledge bearer token utilities
 *
 * Copyright (c) 2021 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Massimiliano Pinto
 */
#include <server_http.hpp>
#include <string>

#define AUTH_HEADER "Authorization"
#define BEARER_SCHEMA "Bearer "

using namespace std;
using HttpServer = SimpleWeb::Server<SimpleWeb::HTTP>;

/**
 * Extract access bearer token from request object
 *
 * @param request	HTTP request object
 * @return		Access token as std::string
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

#endif
