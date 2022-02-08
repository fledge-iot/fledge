#ifndef _LIBCURL_HTTPS_H
#define _LIBCURL_HTTPS_H
/*
 * Fledge HTTP Sender wrapper.
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
#include <fstream>

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
     * Set the proxy host and port
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

    std::string getHostPort()     { return m_host_port; };
	std::string getHTTPResponse() { return m_HTTPResponse; };

private:
	// Make private the copy constructor and operator=
	LibcurlHttps(const LibcurlHttps&);
	LibcurlHttps&     operator=(LibcurlHttps const &);

    	void setLibCurlOptions(CURL *sender, const std::string& path, const vector<pair<std::string, std::string>>& headers);

private:
	CURL               *m_sender;
	std::string         m_HTTPResponse;
	std::string         m_host_port;
	unsigned int        m_retry_sleep_time;       // Seconds between each retry
	unsigned int        m_max_retry;              // Max number of retries in the communication
	std::string         m_authMethod;             // Authentication method to be used
	std::string         m_authBasicCredentials;   // Credentials is the base64 encoding of id and password joined by a single colon (:)
    	struct curl_slist  *m_chunk = NULL;
	unsigned int        m_request_timeout;
	unsigned int        m_connect_timeout;

	// OCS configurations
	std::string	m_OCSNamespace;
	std::string	m_OCSTenantId;
	std::string	m_OCSClientId;
	std::string	m_OCSClientSecret;
	std::string	m_OCSToken;
	std::ofstream	m_ofs;
	bool		m_log;
};

#endif
