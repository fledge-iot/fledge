/*
 * Fledge HTTPS Sender implementation using the libcurl library
 *  - https://curl.haxx.se/libcurl/
 *  - https://github.com/curl/curl
 *
 * Fledge uses the libcurl library to support the Kerberos authentication
 *
 * Copyright (c) 2019 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Stefano Simonelli
 */

#include <thread>
#include <logger.h>
#include <vector>
#include <sstream>
#include <string.h>
#include <stdlib.h>
#include <curl/curl.h>
#include <unistd.h>

#include "libcurl_https.h"
#include "string_utils.h"

#define VERBOSE_LOG      0

#define HTTP_HEADER_LINE 255

using namespace std;

/**
 * Creates a UTC time string for the current time
 *
 * @return		      Current UTC time
 */
static std::string CurrentTimeString()
{
	time_t now = time(NULL);
	struct tm timeinfo;
	gmtime_r(&now, &timeinfo);
	char timeString[20];
	strftime(timeString, sizeof(timeString), "%F %T", &timeinfo);
	return std::string(timeString);
}

/**
 * Constructor: host:port, connect_timeout, request_timeout,
 *              retry_sleep_Time, max_retry
 *
 * Logs the messages into omf.log if the file is present
 */
LibcurlHttps::LibcurlHttps(const string& host_port,
			 unsigned int connect_timeout,
			 unsigned int request_timeout,
			 unsigned int retry_sleep_Time,
			 unsigned int max_retry) :
			HttpSender(),
			m_connect_timeout(connect_timeout),
			m_request_timeout(request_timeout),
			m_host_port(host_port),
			m_retry_sleep_time(retry_sleep_Time),
			m_max_retry (max_retry)
{

	if (curl_global_init(CURL_GLOBAL_DEFAULT) != 0)
	{
		Logger::getLogger()->error("libcurl_https - curl_global_init failed, the libcurl library cannot be initialized.");
	}
	char fname[180];
	if (getenv("FLEDGE_DATA"))
		snprintf(fname, sizeof(fname), "%s/omf.log", getenv("FLEDGE_DATA"));
	else if (getenv("FLEDGE_ROOT"))
		snprintf(fname, sizeof(fname), "%s/data/omf.log", getenv("FLEDGE_ROOT"));
	if (access(fname, W_OK) == 0)
	{
		m_log = true;
		m_ofs.open(fname, ofstream::app);
	}
	else
	{
		m_log = false;
	}
}

/**
 * Destructor
 */
LibcurlHttps::~LibcurlHttps()
{
	if (m_log)
	{
		m_ofs.close();
	}
	curl_global_cleanup();
}

/**
 * Add a proxy server
 *
 * @param proxy	The host and port of the proxy
 */
void LibcurlHttps::setProxy(const string& proxy)
{
	curl_easy_setopt(m_sender, CURLOPT_PROXY, proxy.c_str());
}

/**
 * Avoid libcurl debug messages
 */
size_t cb_write_data(void *buffer, size_t size, size_t nmemb, void *userp)
{
	return size * nmemb;
}

/**
 * Handle the call back header to retrieve the text message in response to an HTTP request
 * this call back is called for all the headers lines
 *
 * received header is nitems * size long in 'buffer' NOT ZERO TERMINATED
 * userdata' is set with CURLOPT_HEADERDATA
 *
 * @param buffer        Header message
 * @param size          (nitems * size) is the size of 'buffer'
 * @param nitems
 * @param userdata out  Buffer to store the data needed
 *
 */
static size_t cb_header(char *buffer, size_t size, size_t nitems, void *userdata)
{

	char *header = (char *)  userdata;
	int  numBytes = 0;
	bool getHeader = false;

	// Only the first line of the headers is needed
	if (*header == '\0')
	{
		getHeader = true;
	}
	else
	{
		// in some situations as using Kerberos
		// the last header starting with HTTP contains the real error
		char tmpBuffer[10];
		sprintf(tmpBuffer, "%.*s", 4, buffer);

		string tmpStr = tmpBuffer;
		for (auto & c: tmpStr) c = toupper(c);

		if (tmpStr.compare("HTTP") == 0) {

			getHeader = true;
		}

	}

	if (getHeader)
	{
		if ((size * nitems) < (HTTP_HEADER_LINE - 1))
			numBytes = size * nitems;
		else
			numBytes = HTTP_HEADER_LINE - 1;

		sprintf(header, "%.*s", numBytes, buffer);
	}
	return nitems * size;
}

/**
 * Setups the libcurl general options used in all the HTTP methods
 *
 * @param sender    libcurl handle on which the options should be configured
 * @param path      The URL path
 * @param headers   The optional headers to send
 *
 */
void LibcurlHttps::setLibCurlOptions(CURL *sender, const string& path, const vector<pair<string, string>>& headers)
{
	string httpHeader;

#if VERBOSE_LOG
	curl_easy_setopt(m_sender, CURLOPT_VERBOSE, 1L);
#else
	curl_easy_setopt(m_sender, CURLOPT_VERBOSE, 0L);
	// this workaround is needed to avoid all libcurl debug messages
	curl_easy_setopt(m_sender, CURLOPT_WRITEFUNCTION, cb_write_data);
#endif
	curl_easy_setopt(m_sender, CURLOPT_NOPROGRESS, 1L);
	curl_easy_setopt(m_sender, CURLOPT_TCP_KEEPALIVE, 1L);

	curl_easy_setopt(m_sender, CURLOPT_TIMEOUT,        m_request_timeout);
	curl_easy_setopt(m_sender, CURLOPT_CONNECTTIMEOUT, m_connect_timeout);

	// HTTP headers handling
	m_chunk = curl_slist_append(m_chunk, "User-Agent: " HTTP_SENDER_USER_AGENT);

	// To let PI Web API having Cross-Site Request Forgery (CSRF) enabled as by default configuration
	m_chunk = curl_slist_append(m_chunk, "X-Requested-With: XMLHttpRequest");

	for (auto it = headers.begin(); it != headers.end(); ++it)
	{
		httpHeader = (*it).first + ": " + (*it).second;
		m_chunk = curl_slist_append(m_chunk, httpHeader.c_str());
	}

	// Handle basic authentication
	if (m_authMethod == "b")
	{
		httpHeader = "Authorization: Basic " + m_authBasicCredentials;
		m_chunk = curl_slist_append(m_chunk, httpHeader.c_str());

		/* set user name and password for the authentication */
		//curl_easy_setopt(m_sender, CURLOPT_USERPWD, "user:pwd");
	}
	curl_easy_setopt(m_sender, CURLOPT_HTTPHEADER, m_chunk);

	// Handle Kerberos authentication
	if (m_authMethod == "k")
	{
		Logger::getLogger()->debug("Kerberos authentication - keytab file :%s: ", getenv("KRB5_CLIENT_KTNAME"));

		curl_easy_setopt(m_sender, CURLOPT_HTTPAUTH, CURLAUTH_GSSNEGOTIATE);
		// The empty user should be defined for Kerberos authentication
		curl_easy_setopt(m_sender, CURLOPT_USERPWD, ":");
	}

	// Configure libcurl
	string url = "https://" + m_host_port + path;

	curl_easy_setopt(m_sender, CURLOPT_URL, url.c_str());

	// Setup SSL
	curl_easy_setopt(m_sender, CURLOPT_USE_SSL, CURLUSESSL_ALL);
	curl_easy_setopt(m_sender, CURLOPT_SSL_VERIFYPEER, 0L);
	curl_easy_setopt(m_sender, CURLOPT_SSL_VERIFYHOST, 0L);
	curl_easy_setopt(m_sender, CURLOPT_HTTP_VERSION, (long)CURL_HTTP_VERSION_2TLS);
}

/**
 * Send data, it retries the operation m_max_retry times
 * waiting m_retry_sleep_time*2 at each attempt
 *
 * @param method    The HTTP method (GET, POST, ...)
 * @param path      The URL path
 * @param headers   The optional headers to send
 * @param payload   The optional data payload (for POST, PUT)
 * @return          The HTTP code for the cases : 1xx Informational /
 *                                                2xx Success /
 *                                                3xx Redirection
 * @throw	    BadRequest for HTTP 400 error
 *		    std::exception as generic exception for all the
 *		    cases >= 401 Client errors / 5xx Server errors
 */
int LibcurlHttps::sendRequest(
		const string& method,
		const string& path,
		const vector<pair<string, string>>& headers,
		const string& payload
)
{
	// Variables definition
	long   httpCode = 0;
	string httpResponseText;
	char   httpHeaderBuffer[HTTP_HEADER_LINE];

	bool retry = false;
	int  retryCount = 1;
	int  sleepTime = m_retry_sleep_time;

	CURLcode res = CURLE_OK;

	enum exceptionType
	{
	    none, typeBadRequest, typeException
	};

	exceptionType exceptionRaised = none;
	string exceptionMessage;
	string errorMessage;

	// Init libcurl
	m_sender = curl_easy_init();
	if(m_sender)
	{
		setLibCurlOptions(m_sender, path, headers);
	}
	else
	{
		string errorMessage = "libcurl_https - curl_easy_init failed, the libcurl library cannot be initialized.";

		Logger::getLogger()->error(errorMessage);
		throw runtime_error(errorMessage.c_str());
	}

	// Select the requested HTTP method
	if (method.compare("POST") == 0)
	{
		curl_easy_setopt(m_sender, CURLOPT_POST, 1L);

		curl_easy_setopt(m_sender, CURLOPT_POSTFIELDS,           payload.c_str());
		curl_easy_setopt(m_sender, CURLOPT_POSTFIELDSIZE, (long) payload.length());
	}
	else if (method.compare("GET") == 0)
	{
		// TODO : to be implemented
		errorMessage = "libcurl_https - method GET is not currently implemented";
		Logger::getLogger()->debug(errorMessage);
		throw runtime_error(errorMessage);
	}
	else if (method.compare("PUT") == 0)
	{
		// TODO : to be implemented
		errorMessage = "libcurl_https - method PUT currently not implemented";
		Logger::getLogger()->debug("libcurl_https - method PUT is not currently implemented");
		throw runtime_error(errorMessage);

	}
	else if (method.compare("DELETE") == 0)
	{
		// TODO : to be implemented
		errorMessage = "libcurl_https - method DELETE currently not implemented";
		Logger::getLogger()->debug("libcurl_https - method DELETE is not currently implemented ");
		throw runtime_error(errorMessage);
	}

	do
	{
		std::chrono::high_resolution_clock::time_point tStart;
		try
		{
			exceptionRaised = none;
			httpCode = 0;
			httpResponseText = "";
			httpHeaderBuffer[0] = '\0';

			// It is needed to handle the call back header to retrieve the text message
			// in response to an HTTP request
			// curl.haxx.se/mail/lib-2013-10/0114.html
			curl_easy_setopt(m_sender, CURLOPT_HEADERDATA,     httpHeaderBuffer);
			curl_easy_setopt(m_sender, CURLOPT_HEADERFUNCTION, cb_header);
			if (m_log)
			{
				m_ofs << endl << method << " " << path << endl;
				m_ofs << "Headers" << endl;
				for (auto it = headers.begin(); it != headers.end(); it++)
				{
					m_ofs << "    " << it->first << ": " << it->second << endl;
				}
				m_ofs << "Payload:" << endl;
				m_ofs << payload << endl;
				tStart = std::chrono::high_resolution_clock::now();
			}

			// Execute the HTTP method
			res = curl_easy_perform(m_sender);

			curl_easy_getinfo(m_sender, CURLINFO_RESPONSE_CODE, &httpCode);

			// fix the text message
			// NOTE : the text should be considered only if the HTTP code is not an ACK
			httpResponseText = httpHeaderBuffer;
			if (m_log)
			{
				std::chrono::high_resolution_clock::time_point tEnd = std::chrono::high_resolution_clock::now();
				m_ofs << "Response:" << endl;
				m_ofs << "   Code: " << httpCode << endl;
				m_ofs << "   Time: " << ((double)std::chrono::duration_cast<std::chrono::microseconds>(tEnd - tStart).count()) / 1.0E6 << " sec     " << CurrentTimeString() << endl;
				m_ofs << "   Content: " << httpResponseText << endl << endl;
			}
			StringStripCRLF(httpResponseText);

			m_HTTPResponse = httpResponseText;
		}
		catch (exception &ex)
		{
			exceptionRaised = typeException;
			errorMessage = "Failed to send data: ";
			errorMessage.append(ex.what());
		}


		if ( (res == CURLE_OK )                          &&
		     (exceptionRaised == none )                  &&
		     ((httpCode >= 200) && (httpCode <= 399))
		     )
		{
			retry = false;
#if VERBOSE_LOG
			Logger::getLogger()->info("HTTPS sendRequest succeeded : retry count |%d| HTTP code |%d|",
						  retryCount,
						  httpCode);
#endif
		}
		else
		{
			if (res != CURLE_OK)
			{
				errorMessage = string(curl_easy_strerror(res) );
				if (httpResponseText.compare("") != 0 )
					errorMessage += " - " + httpResponseText;
			}
			else
			{
				// the situation is : CURLE_OK but the httpCode reports an error
				errorMessage = httpResponseText;
			}

#if VERBOSE_LOG
			if (exceptionRaised)
			{
				Logger::getLogger()->error(
					"HTTPS sendRequest : retry count |%d| error |%s| message |%s|",
					retryCount,
					errorMessage.c_str(),
					payload.c_str());

			}
			else
			{
				Logger::getLogger()->error(
					"HTTPS sendRequest : retry count |%d| HTTP code |%d| error message |%s| HTTP message |%s|",
					retryCount,
					httpCode,
					errorMessage.c_str(),
					payload.c_str());
			}
#endif

			if (m_log && !errorMessage.empty())
			{
				std::chrono::high_resolution_clock::time_point tEnd = std::chrono::high_resolution_clock::now();
				m_ofs << "   Time: " << ((double)std::chrono::duration_cast<std::chrono::microseconds>(tEnd - tStart).count()) / 1.0E6 << " sec     " << CurrentTimeString() << endl;
				m_ofs << "   Exception: " << errorMessage << endl;
			}

			if (retryCount < m_max_retry)
			{
				this_thread::sleep_for(chrono::seconds(sleepTime));

				retry = true;
				sleepTime *= 2;
				retryCount++;
			}
			else
			{
				retry = false;
			}

		}
	} while (retry);

	// Cleanup
	curl_easy_cleanup(m_sender);
	curl_slist_free_all(m_chunk);
	m_sender = NULL;
	m_chunk = NULL;

	// Check if an error should be raised
	if (exceptionRaised == none)
	{
		// 0 = HTTP failed without an HTTP code
		if (httpCode == 0)
		{
			throw runtime_error(errorMessage);
		}
		else if (httpCode == 400)
		{
			throw BadRequest(errorMessage);
		}
		else if (httpCode == 401)
		{
			throw Unauthorized(errorMessage);
		}
		else if (httpCode == 409)
		{
			throw Conflict(errorMessage);
		}
		else if (httpCode >= 401)
		{
			string errorMessageHTTP;
			errorMessageHTTP = "HTTP code |" + to_string(httpCode) +  "| - HTTP error |" + errorMessage + "|";

			throw runtime_error(errorMessageHTTP);
		}
	}
	else
	{
		throw runtime_error(errorMessage);
	}

	return httpCode;
}
