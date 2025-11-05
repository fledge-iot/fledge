/*
 * Fledge OSIsoft OMF interface to PI Server.
 *
 * Copyright (c) 2023 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */

#include <utility>
#include <iostream>
#include <string>
#include <cstring>
#include <logger.h>
#include "string_utils.h"

#include <iterator>
#include <typeinfo>
#include <algorithm>

#include <omferror.h>
#include <rapidjson/error/en.h>

#include <stdio.h>

using namespace std;
using namespace rapidjson;

/**
 * Constructors
 */
OMFError::OMFError() : m_hasErrors(false)
{
}

OMFError::OMFError(const string& json)
{
	setFromHttpResponse(json);
}

/**
 * Destructor for the error class
 */
OMFError::~OMFError()
{
}

/**
 * Parse error information from an OMF POST response JSON document
 *
 * @param json	JSON response document from an OMF POST
 */
void OMFError::setFromHttpResponse(const string& json)
{
	m_messages.clear();
	m_hasErrors = false;

	char *p = (char *)json.c_str();

	FILE *fp = fopen("/tmp/error", "a");
	fprintf(fp, "%s\n\n", p);
	fclose(fp);

	while (*p && *p != '{')
		p++;
	Document doc;
	if (doc.ParseInsitu(p).HasParseError())
	{
		Logger::getLogger()->error("Unable to parse response from OMF endpoint: %s",
								   GetParseError_En(doc.GetParseError()));
		Logger::getLogger()->error("Error response was: %s", json.c_str());
	}
	else if (doc.HasMember("Messages") && doc["Messages"].IsArray())
	{
		const Value& messages = doc["Messages"].GetArray();

		for (Value::ConstValueIterator a = messages.Begin(); a != messages.End(); a++)
		{
			const Value& msg = *a;
			int httpCode = 200;
			if (msg.HasMember("Status") && msg["Status"].IsObject())
			{
				const Value& status = msg["Status"];
				if (status.HasMember("Code") && status["Code"].IsInt())
				{
					httpCode = status["Code"].GetInt();
				}
			}
			if (msg.HasMember("Events") && msg["Events"].IsArray())
			{
				const Value& events = msg["Events"];
				for (Value::ConstValueIterator b = events.Begin(); b != events.End(); b++)
				{
					const Value &event = *b;
					string message, reason, severity, exceptionType, exceptionMessage;

					// ExceptionInfo can appear inside an Event object
					// or inside an Event->InnerEvents object 
					if (event.HasMember("ExceptionInfo") && event["ExceptionInfo"].IsObject())
					{
						const Value &exceptionInfo = event["ExceptionInfo"];
						if (exceptionInfo.HasMember("Type") && exceptionInfo["Type"].IsString())
						{
							exceptionType = exceptionInfo["Type"].GetString();
						}
						if (exceptionInfo.HasMember("Message") && exceptionInfo["Message"].IsString())
						{
							exceptionMessage = exceptionInfo["Message"].GetString();
							std::string crlf(2, '\r');
							crlf[1] = '\n';
							StringReplaceAll(exceptionMessage, crlf, " ");
							exceptionMessage = StringStripWhiteSpacesExtra(exceptionMessage);
						}
					}
					else if (event.HasMember("InnerEvents") && event["InnerEvents"].IsArray())
					{
						rapidjson::GenericArray<true, rapidjson::Value> innerEvents = event["InnerEvents"].GetArray();
						if (innerEvents.Size() > 0)
						{
							const Value &innerEvent = innerEvents[0];
							if (innerEvent.HasMember("ExceptionInfo") && innerEvent["ExceptionInfo"].IsObject())
							{
								const Value &exceptionInfo = innerEvent["ExceptionInfo"];
								if (exceptionInfo.HasMember("Type") && exceptionInfo["Type"].IsString())
								{
									exceptionType = exceptionInfo["Type"].GetString();
								}
								if (exceptionInfo.HasMember("Message") && exceptionInfo["Message"].IsString())
								{
									exceptionMessage = exceptionInfo["Message"].GetString();
									std::string crlf(2, '\r');
									crlf[1] = '\n';
									StringReplaceAll(exceptionMessage, crlf, " ");
									exceptionMessage = StringStripWhiteSpacesExtra(exceptionMessage);
								}
							}
						}
					}
					if (event.HasMember("Severity") && event["Severity"].IsString())
					{
						severity = event["Severity"].GetString();
						if (severity.compare("Error") == 0)
						{
							m_hasErrors = true;
						}
					}
					if (event.HasMember("EventInfo") && event["EventInfo"].IsObject())
					{
						const Value& eventInfo = event["EventInfo"];
						if (eventInfo.HasMember("Message") && eventInfo["Message"].IsString())
						{
							message = eventInfo["Message"].GetString();
						}
						if (eventInfo.HasMember("Reason") && eventInfo["Reason"].IsString())
						{
							reason = eventInfo["Reason"].GetString();
						}
					}
					m_messages.push_back(Message(severity, message, reason, exceptionType, exceptionMessage, httpCode));
				}
			}
		}
	}
}

/**
 * Return the most severe HTTP Code from all messages.
 * PI Web API HTTP Codes are usually the same within one HTTP response.
 * 
 * @return HTTP Code
 */
int OMFError::getHttpCode()
{
	int httpCode = 200;

	for (Message &msg : m_messages)
	{
		if (msg.getHttpCode() > httpCode)
		{
			httpCode = msg.getHttpCode();
		}
	}

	return httpCode;
}

/**
 * Return the error message for the given message
 *
 * @param offset	The error within the report to return
 * @return string	The event message
 */
string OMFError::getMessage(unsigned int offset)
{
string rval;

	if (offset < messageCount())
	{
		rval = m_messages[offset].getMessage();
	}
	return rval;
}

/**
 * Return the error reason for the given message
 *
 * @param offset	The error within the report to return
 * @return string	The event reason
 */
string OMFError::getEventReason(unsigned int offset)
{
string rval;

	if (offset < messageCount())
	{
		rval = m_messages[offset].getReason();
	}
	return rval;
}

/**
 * Get the event severity for a given message
 *
 * @param offset	The message to examine
 * @return string	The event severity
 */
string OMFError::getEventSeverity(unsigned int offset)
{
string rval;

	if (offset < messageCount())
	{
		rval = m_messages[offset].getSeverity();
	}
	return rval;
}

/**
 * Get the event exception type for a given message
 *
 * @param offset	The message to examine
 * @return string	The event exception type
 */
string OMFError::getEventExceptionType(unsigned int offset)
{
string rval;

	if (offset < messageCount())
	{
		rval = m_messages[offset].getExceptionType();
	}
	return rval;
}

/**
 * Get the event exception message for a given message
 *
 * @param offset	The message to examine
 * @return string	The event exception message
 */
string OMFError::getEventExceptionMessage(unsigned int offset)
{
string rval;

	if (offset < messageCount())
	{
		rval = m_messages[offset].getExceptionMessage();
	}
	return rval;
}

/**
 * Log all available messages
 *
 * @param mainMessage       Top-level message when reporting an error
 * @param filterDuplicates  If true, do not log duplicate messages
 * @return                  True if OMFError object holds at least one message
 */
bool OMFError::Log(const std::string &mainMessage, bool filterDuplicates)
{
	if (hasMessages())
	{
		if (hasErrors())
		{
			Logger::getLogger()->error("HTTP %d: %s: %u %s",
									   getHttpCode(),
									   mainMessage.c_str(),
									   messageCount(),
									   (messageCount() == 1) ? "message" : "messages");
		}
		else
		{
			Logger::getLogger()->warn("HTTP %d: %s: %u %s",
									  getHttpCode(),
									  mainMessage.c_str(),
									  messageCount(),
									  (messageCount() == 1) ? "message" : "messages");
		}

		std::string lastMessage;
		std::string lastExceptionMessage;
		unsigned int numDuplicates = 0;

		for (unsigned int i = 0; i < messageCount(); i++)
		{
			Message &msg = m_messages[i];
			std::string errorMessage = msg.getMessage();
			std::string exceptionMessage = msg.getExceptionMessage();

			if (filterDuplicates && (0 == errorMessage.compare(lastMessage)) && (0 == exceptionMessage.compare(lastExceptionMessage)))
			{
				numDuplicates++;
			}
			else
			{
				if (msg.getSeverity().compare("Error") == 0)
				{
					Logger::getLogger()->error("Message %u HTTP %d: %s, %s, %s",
											   i,
											   msg.getHttpCode(),
											   msg.getSeverity().c_str(),
											   errorMessage.c_str(),
											   msg.getReason().c_str());
				}
				else
				{
					Logger::getLogger()->warn("Message %u HTTP %d: %s, %s, %s",
											  i,
											  msg.getHttpCode(),
											  msg.getSeverity().c_str(),
											  errorMessage.c_str(),
											  msg.getReason().c_str());
				}

				if (!exceptionMessage.empty() && (0 != errorMessage.compare(exceptionMessage)))
				{
					Logger::getLogger()->error("Message %u Exception: %s (%s)",
											   i,
											   exceptionMessage.c_str(),
											   msg.getExceptionType().c_str());
				}

				lastMessage = errorMessage;
				lastExceptionMessage = exceptionMessage;
			}
		}

		if (numDuplicates > 0)
		{
			Logger::getLogger()->warn("%u duplicate messages skipped", numDuplicates);
		}
	}

	return hasMessages();
}
