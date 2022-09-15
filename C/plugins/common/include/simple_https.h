#ifndef _SIMPLE_HTTPS_H
#define _SIMPLE_HTTPS_H
/*
 * Fledge HTTP Sender wrapper.
 *
 * Copyright (c) 2018 Diamnomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Massimiliano Pinto, Mark Riddoch, Stefano Simonelli
 */

#include <string>
#include <vector>
#include <http_sender.h>
#include <client_https.hpp>
#include <fstream>

using HttpsClient = SimpleWeb::Client<SimpleWeb::HTTPS>;

class SimpleHttps: public HttpSender
{
	public:
		/**
		 * Constructor:
		 * pass host:port, connect & request timeouts
		 */
		SimpleHttps(const std::string& host_port,
			    unsigned int connect_timeout = 0,
			    unsigned int request_timeout = 0,
			    unsigned int retry_sleep_Time = 1,
			    unsigned int max_retry = 4);

		// Destructor
		~SimpleHttps();

		/**
		 * Set the host and port of the proxy server
		 */
		void setProxy(const std::string& proxy);

		/**
		 * HTTP(S) request: pass method and path, HTTP headers and POST/PUT payload.
		 */
		int sendRequest(
				const std::string& method = std::string(HTTP_SENDER_DEFAULT_METHOD),
				const std::string& path = std::string(HTTP_SENDER_DEFAULT_PATH),
				const std::vector<std::pair<std::string, std::string>>& headers = {},
				const std::string& payload = std::string()
		);

		void setAuthMethod          (std::string& authMethod)           {m_authMethod = authMethod; }
		void setAuthBasicCredentials(std::string& authBasicCredentials) {m_authBasicCredentials = authBasicCredentials; }

		// OCS configurations
		void setOCSNamespace         (std::string& OCSNamespace)          {m_OCSNamespace    = OCSNamespace; }
		void setOCSTenantId          (std::string& OCSTenantId)           {m_OCSTenantId     = OCSTenantId; }
		void setOCSClientId          (std::string& OCSClientId)           {m_OCSClientId     = OCSClientId; }
		void setOCSClientSecret      (std::string& OCSClientSecret)       {m_OCSClientSecret = OCSClientSecret; }
		void setOCSToken             (std::string& OCSToken)              {m_OCSToken        = OCSToken; }

		std::string getHTTPResponse() { return m_HTTPResponse; };
		std::string getHostPort()     { return m_host_port; };

	private:
		// Make private the copy constructor and operator=
		SimpleHttps(const SimpleHttps&);
		SimpleHttps&     operator=(SimpleHttps const &);
	private:
		std::string	    m_host_port;
		HttpsClient	   *m_sender;
		std::string	    m_HTTPResponse;
		unsigned int	m_retry_sleep_time;       // Seconds between each retry
		unsigned int	m_max_retry;              // Max number of retries in the communication

		std::string	m_authMethod;             // Authentication method to be used
		std::string	m_authBasicCredentials;   // Credentials is the base64 encoding of id and password joined by a single colon (:)

		// OCS configurations
		std::string	m_OCSNamespace;
		std::string	m_OCSTenantId;
		std::string	m_OCSClientId;
		std::string	m_OCSClientSecret;
		std::string	m_OCSToken;
		bool		m_log;
		std::ofstream	m_ofs;

};

#endif
