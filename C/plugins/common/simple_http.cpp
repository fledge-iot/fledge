/*
 * FogLAMP HTTP Sender implementation using the
 * Simple Web Seerver HTTP library.
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Massimiliano Pinto, Mark Riddoch
 */
#include <simple_http.h>

using namespace std;

// Using https://github.com/eidheim/Simple-Web-Server
using HttpClient = SimpleWeb::Client<SimpleWeb::HTTP>;

/**
 * Constructor: host:port, connect_timeout, request_timeout
 */
SimpleHttp::SimpleHttp(const string& host_port,
		       unsigned int connect_timeout,
		       unsigned int request_timeout) :
		       HttpSender(), m_host_port(host_port)
{
	m_sender = new HttpClient(host_port);
	m_sender->config.timeout = (time_t)request_timeout;
	m_sender->config.timeout_connect = (time_t)connect_timeout;
}

/**
 * Destructor
 */
SimpleHttp::~SimpleHttp()
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
 * @return          The HTTP code on success or 0 on execptions
 */
int SimpleHttp::sendRequest(const string& method,
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

	// Call HTTP method
	try
	{
		auto res = m_sender->request(method, path, payload, header);
		retCode = res->status_code;
	} catch (exception& ex) {
		string errMsg("Failed to send data: ");
		errMsg.append(ex.what());

		throw runtime_error(errMsg);
	}

	return atoi(retCode.c_str());
}
