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
#include <rapidjson/document.h>
#include <logger.h>

using namespace rapidjson;
using namespace std;
using HttpServer = SimpleWeb::Server<SimpleWeb::HTTP>;

/**
 * BearerToken constructor with request object
 *
 * @param request	HTTP request object
 */
BearerToken::BearerToken(shared_ptr<HttpServer::Request> request)
{
string bearer_token;

 	// Extract access bearer token from request headers
	for(auto &field : request->header)
	{
		if (field.first == AUTH_HEADER)
		{
			std::size_t pos = field.second.rfind(BEARER_SCHEMA);
			if (pos != string::npos)
			{
				pos += strlen(BEARER_SCHEMA);
				m_bearer_token = field.second.substr(pos);
			}
		}
	}

	m_expiration = 0;
	m_verified = false;
}

/**
 * BearerToken constructor with string reference
 * @param token		Bearer token string
 */
BearerToken::BearerToken(std::string& token) :
			m_bearer_token(token)
{	
	m_expiration = 0;
	m_verified = false;
}

/**
 * BearerToken verification from JSON string reference
 *
 * Known token claims as stored as strings
 *
 * @param response	JSON string from token verification endpoint
 * @return		True on success
 * 			False otherwise
 */
bool BearerToken::verify(const string& response)
{
	if (m_bearer_token.length() == 0)
	{
		return false;
	}	

	Logger *log = Logger::getLogger();
	Document doc;
	doc.Parse(response.c_str());
	if (doc.HasParseError())
	{
		bool httpError = (isdigit(response[0]) &&
				  isdigit(response[1]) &&
				  isdigit(response[2]) &&
				  response[3]==':');
		log->error("%s error in service token verification: %s\n",
				httpError?"HTTP error during":"Failed to parse result of",
				response.c_str());
		return false;
	}

	// Check JSON error item
	if (doc.HasMember("error"))
	{
		if (doc["error"].IsString())
		{
			string error = doc["error"].GetString();
			log->error("Failed to parse token verification result, error %s",
					error.c_str());
		}
		else
		{
			log->error("Failed to parse token verification result: %s",
					response.c_str());
		}

		return false;
	}

	// Check JSON claim items
	if (doc.HasMember("aud") &&
	    doc.HasMember("sub") &&
	    doc.HasMember("iss") &&
	    doc.HasMember("exp"))
	{
		// Set token claims in the input map
		if (doc["aud"].IsString() &&
		    doc["sub"].IsString() &&
		    doc["iss"].IsString() &&
		    doc["exp"].IsUint())
		{
			// Valid data: set claim values, expiration and verified
			m_audience = doc["aud"].GetString();
			m_subject = doc["sub"].GetString();
			m_issuer = doc["iss"].GetString();
			m_expiration = doc["exp"].GetUint();

			m_verified = true;

			log->debug("Token verified %s:%s, expiration %ld",
				m_audience.c_str(),
				m_subject.c_str(),
				m_expiration);
		}
		else
		{
			log->error("Token claims do not contain valid values: %s",
				response.c_str());
		}
	}
	else
	{
		log->error("Needed token claims not found: %s", response.c_str());
	}

	return m_verified;
}
