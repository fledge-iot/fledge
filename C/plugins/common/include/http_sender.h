#ifndef _HTTP_SENDER_H
#define _HTTP_SENDER_H
/*
 * Fledge HTTP Sender wrapper.
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Massimiliano Pinto
 */

#include <string>
#include <vector>

#define HTTP_SENDER_USER_AGENT     "Fledge http sender"
#define HTTP_SENDER_DEFAULT_METHOD "GET"
#define HTTP_SENDER_DEFAULT_PATH   "/"

class HttpSender
{
	public:
		/**
		 * Constructor:
		 */
		HttpSender();

		// Destructor
		virtual ~HttpSender();

		/**
		 * Set a proxy server
		 */
		virtual void setProxy(const std::string& proxy) = 0;

		/**
		 * HTTP(S) request: pass method and path, HTTP headers and POST/PUT payload.
		 */
		virtual int sendRequest(
				const std::string& method = std::string(HTTP_SENDER_DEFAULT_METHOD),
				const std::string& path = std::string(HTTP_SENDER_DEFAULT_PATH),
				const std::vector<std::pair<std::string, std::string>>& headers = {},
				const std::string& payload = std::string()
		) = 0;

		virtual std::string getHostPort() = 0;
		virtual std::string getHTTPResponse() = 0;

		virtual void setAuthMethod          (std::string& authMethod) = 0;
		virtual void setAuthBasicCredentials(std::string& authBasicCredentials) = 0;

		// OCS configurations
		virtual void setOCSNamespace         (std::string& OCSNamespace) = 0;
		virtual void setOCSTenantId          (std::string& OCSTenantId) = 0;
		virtual	void setOCSClientId          (std::string& OCSClientId) = 0;
		virtual void setOCSClientSecret      (std::string& OCSClientSecret) = 0;
		virtual void setOCSToken             (std::string& OCSToken) = 0;

        /**
         * @brief Constructs the file path for the OMF log based on environment variables.
         *
         * This function checks for the existence of two environment variables:
         * FLEDGE_DATA and FLEDGE_ROOT. It constructs the file path to the OMF log
         * file accordingly. The priority is given to FLEDGE_DATA. If neither
         * environment variable is set, an error message is printed, and an empty
         * string is returned.
         *
         * @return A string representing the path to the OMF log file, or an empty
         *         string if neither environment variable is set.
         */
        static std::string getOMFTracePath();

        /**
         * @brief Creates the "debug-trace" directory under the base directory returned by getDataDir().
         * 
         */
        static bool createDebugTraceDirectory();
};

/**
 * BadRequest exception
 */
class BadRequest : public std::exception {
	public:
		// Constructor with parameter
		BadRequest(const std::string& serverReply)
		{
			m_errmsg = serverReply;
		};

		virtual const char *what() const throw()
		{
			return m_errmsg.c_str();
		}

	private:
		std::string     m_errmsg;
};

/**
 * Unauthorized  exception
 */
class Unauthorized  : public std::exception {
	public:
		// Constructor with parameter
		Unauthorized (const std::string& serverReply)
		{
			m_errmsg = serverReply;
		};

		virtual const char *what() const throw()
		{
			return m_errmsg.c_str();
		}

	private:
		std::string     m_errmsg;
};

/**
 * Conflict  exception
 */
class Conflict  : public std::exception {
	public:
		// Constructor with parameter
		Conflict (const std::string& serverReply)
		{
			m_errmsg = serverReply;
		};

		virtual const char *what() const throw()
		{
			return m_errmsg.c_str();
		}

	private:
		std::string     m_errmsg;
};

#endif
