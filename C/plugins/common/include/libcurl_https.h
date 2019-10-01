#ifndef _LIBCURL_HTTPS_H
#define _LIBCURL_HTTPS_H
/*
 * FogLAMP HTTP Sender wrapper.
 *
 * Copyright (c) 2019 Diamnomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Stefano Simonelli
 */

#include <string>
#include <vector>
#include <http_sender.h>
#include <curl/curl.h>

using namespace std;

class LibcurlHttps:  public HttpSender
{
public:
    /**
     * Constructor:
     * pass host:port, connect & request timeouts, retry_sleep_Time, max_retry
     */
    LibcurlHttps(const std::string& host_port,
		unsigned int connect_timeout = 0,
		unsigned int request_timeout = 0,
		unsigned int retry_sleep_Time = 1,
		unsigned int max_retry = 4);

    // Destructor
    ~LibcurlHttps();

    /**
     * HTTP(S) request: pass method and path, HTTP headers and POST/PUT payload.
     */
    int sendRequest(const std::string& method = std::string(HTTP_SENDER_DEFAULT_METHOD),
		    const std::string& path = std::string(HTTP_SENDER_DEFAULT_PATH),
		    const std::vector<std::pair<std::string, std::string>>& headers = {},
		    const std::string& payload = std::string());

    void setAuthMethod          (std::string& authMethod)           {m_authMethod = authMethod; }
    void setAuthBasicCredentials(std::string& authBasicCredentials) {m_authBasicCredentials = authBasicCredentials; }

    std::string getHostPort() { return m_host_port; };

private:
	// Make private the copy constructor and operator=
	LibcurlHttps(const LibcurlHttps&);
	LibcurlHttps&     operator=(LibcurlHttps const &);

    	void setLibCurlOptions(CURL *sender, const std::string& path, const vector<pair<std::string, std::string>>& headers);

private:
	CURL               *m_sender;
	std::string         m_host_port;
	unsigned int        m_retry_sleep_time;       // Seconds between each retry
	unsigned int        m_max_retry;              // Max number of retries in the communication
	std::string         m_authMethod;             // Authentication method to be used
	std::string         m_authBasicCredentials;   // Credentials is the base64 encoding of id and password joined by a single colon (:)
    	struct curl_slist  *m_chunk = NULL;
	unsigned int        m_request_timeout;
	unsigned int        m_connect_timeout;
};

#endif
