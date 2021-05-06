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

using namespace std;
using HttpServer = SimpleWeb::Server<SimpleWeb::HTTP>;

string getBearerToken(shared_ptr<HttpServer::Request> request)
{
        string bearer_token;

        for(auto &field : request->header)
        {
                if (field.first == "Authorization")
                {
                        std::size_t pos = field.second.rfind("Bearer ");
                        if (pos != string::npos)
                        {
                                pos += strlen("Bearer ");
                                bearer_token = field.second.substr(pos);
                        }
                }
        }

        return bearer_token;
}
#endif
