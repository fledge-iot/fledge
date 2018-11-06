/*
 * FogLAMP HTTP Sender implementation using the
 * HTTPS Simple Web Server library
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Massimiliano Pinto, Mark Riddoch
 */

#include <simple_https.h>

using namespace std;

// Using https://github.com/eidheim/Simple-Web-Server
using HttpsClient = SimpleWeb::Client<SimpleWeb::HTTPS>;

/**
 * Constructor: host:port, connect_timeout, request_timeout
 */
SimpleHttps::SimpleHttps(const string& host_port,
                         unsigned int connect_timeout,
                         unsigned int request_timeout) :
			 HttpSender(), m_host_port(host_port)
{
	// Passing false to second parameter avoids certificate verification
	m_sender = new HttpsClient(host_port, false);
	m_sender->config.timeout = (time_t)request_timeout;
	m_sender->config.timeout_connect = (time_t)connect_timeout;
}

/**
 * Destructor
 */
SimpleHttps::~SimpleHttps()
{
	delete m_sender;
}

/**
 * Send data
 *
 * @param method    The HTTP method (GET, POST, ...)
 * @param path      The URL path
 * @param headers   The optional headers to send
 * @param payload   The optional data payload (for POST, PUT)
 * @return          The HTTP code for the cases : 1xx Informational / 2xx Success / 3xx Redirection
 * @throw	    BadRequest for HTTP 400 error
 *		    std::exception as generic exception for all the cases >= 401 Client errors / 5xx Server errors
 */
int SimpleHttps::sendRequest(const string& method,
			    const string& path,
			    const vector<pair<string, string>>& headers,
			    const string& payload)
{
	SimpleWeb::CaseInsensitiveMultimap header;

	// Add FogLAMP UserAgent
	header.emplace("User-Agent", HTTP_SENDER_USER_AGENT);

	// Add custom headers
	for (auto it = headers.begin(); it != headers.end(); ++it)
	{
		header.emplace((*it).first, (*it).second);
	}

	string retCode;

	// Call HTTPS method
	try
	{
		auto res = m_sender->request(method, path, payload, header);
		retCode = res->status_code;
		string response = res->content.string();

		int http_code = atoi(retCode.c_str());

		// If 400 Bad Request, throw BadRequest exception
		if (http_code == 400)
		{
			throw BadRequest(response);
		}
		else  if (http_code >= 401)
		{
			std::stringstream error_message;
			error_message << "HTTP code |" << to_string(http_code) << "| HTTP error |" << response << "|";

			throw runtime_error(error_message.str());
		}

	} catch (BadRequest& ex) {
		throw BadRequest(ex.what());
	} catch (exception& ex) {
		string errMsg("Failed to send data: ");
		errMsg.append(ex.what());

		throw runtime_error(errMsg); 
	}

	return atoi(retCode.c_str());
}
