#ifndef _SIMPLE_HTTP_H
#define _SIMPLE_HTTP_H
/*
 * FogLAMP HTTP Sender wrapper.
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Massimiliano Pinto, Mark Riddoch
 */

#include <string>
#include <vector>
#include <http_sender.h>
#include <client_http.hpp>

using HttpClient = SimpleWeb::Client<SimpleWeb::HTTP>;

class SimpleHttp: public HttpSender
{
	public:
		/**
		 * Constructor: pass host:port & connect & request timeouts
		 */
		SimpleHttp(const std::string& host_port,
				unsigned int connect_timeout = 0,
				unsigned int request_timeout = 0);

		// Destructor
		~SimpleHttp();

		/**
		 * HTTP(S) request: pass method and path, HTTP headers and POST/PUT payload.
		 */
		int sendRequest(const std::string& method = std::string(HTTP_SENDER_DEFAULT_METHOD),
				const std::string& path = std::string(HTTP_SENDER_DEFAULT_PATH),
				const std::vector<std::pair<std::string, std::string>>& headers = {},
				const std::string& payload = std::string());

		std::string getHostPort() { return m_host_port; };
	private:
		// Make private the copy constructor and operator=
		SimpleHttp(const SimpleHttp&);
		SimpleHttp&	operator=(SimpleHttp const &);

	private:
		std::string	m_host_port;
		HttpClient	*m_sender;
		
};

#endif
