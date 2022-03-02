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

/**
 * This class represents a JWT bearer token
 *
 * The claims are stored after verification to core service API endpoint
 *
 */
class BearerToken
{
	public:
		BearerToken(std::shared_ptr<SimpleWeb::Server<SimpleWeb::HTTP>::Request> request);
		BearerToken(std::string& token);
		~BearerToken() {};
		bool		exists()
		{
			return m_bearer_token.length() > 0;
		};
		// Return string reference
		const std::string&
				token() { return m_bearer_token; };
		bool		verify(const std::string& serverResponse);
		unsigned long	getExpiration() { return m_expiration; };
		// Return string references
		const std::string&
				getAudience() { return m_audience; };
		const std::string&
				getSubject() { return m_subject; };
		const std::string&
				getIssuer() { return m_issuer; };

	private:
		bool		m_verified;
		unsigned long	m_expiration;
		std::string	m_bearer_token;
		std::string	m_audience;
		std::string	m_subject;
		std::string	m_issuer;
};

#endif
