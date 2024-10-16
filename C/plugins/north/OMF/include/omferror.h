#ifndef _OMFERROR_H
#define _OMFERROR_H
/*
 * Fledge OSIsoft OMF interface to PI Server.
 *
 * Copyright (c) 2023 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */

#include <rapidjson/document.h>
#include <string>
#include <vector>

/**
 * An encapsulation of an error return from an OMF call.
 * The class parses the JSON response and gives access to portion of that JSON response.
 */
class OMFError {
	public:
		OMFError();
		OMFError(const std::string& json);
		~OMFError();

		unsigned int	messageCount();
		std::string	getMessage(unsigned int offset);
		std::string	getEventReason(unsigned int offset);
		std::string	getEventSeverity(unsigned int offset);
		int			getHttpCode();
		void setFromHttpResponse(const std::string& json);
		/**
		 * The error report contains at least one error level event
		 */
		bool		hasErrors() { return m_hasErrors; };
	private:
		unsigned int		m_messageCount;
		class Message {
			public:
				Message(const std::string& severity,
						const std::string& message,
						const std::string& reason,
						const int httpCode) :
					m_severity(severity),
					m_message(message),
					m_reason(reason),
					m_httpCode(httpCode)
				{
				};
				std::string	getSeverity() { return m_severity; };
				std::string	getMessage() { return m_message; };
				std::string	getReason() { return m_reason; };
				int	getHttpCode() { return m_httpCode; };
			private:
				std::string	m_severity;
				std::string	m_message;
				std::string	m_reason;
				int			m_httpCode;
		};
		std::vector<Message>	m_messages;
		bool			m_hasErrors;
};
#endif
