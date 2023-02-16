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
 * Constructor
 */
OMFError::OMFError(const string& json) : m_messageCount(0)
{
	char *p  = (char *)json.c_str();

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
		m_messageCount = messages.Size();

		for (Value::ConstValueIterator a = messages.Begin(); a != messages.End(); a++)
		{
			const Value& msg = *a;
			if (msg.HasMember("Events") && msg["Events"].IsArray())
			{
				const Value& events = msg["Events"];
				const Value& event = events[0];
				string message, reason, severity;
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
				m_messages.push_back(Message(severity, message, reason));
			}
		}
	}
}

/**
 * Destructor for the error class
 */
OMFError::~OMFError()
{
}

/**
 * Return the number of messages within the error report
 */
unsigned int OMFError::messageCount()
{
	return m_messageCount;
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

	if (offset < m_messageCount)
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

	if (offset < m_messageCount)
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

	if (offset < m_messageCount)
	{
		rval = m_messages[offset].getSeverity();
	}
	return rval;
}

