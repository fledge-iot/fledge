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

std::string getAccessBearerToken(std::shared_ptr<SimpleWeb::Server<SimpleWeb::HTTP>::Request> request);

#endif
