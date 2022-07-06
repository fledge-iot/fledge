/*
 * Fledge category management
 *
 * Copyright (c) 2022 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Massimiliano Pinto
 */

#include <logger.h>
#include <stdexcept>
#include <acl.h>
#include <rapidjson/document.h>
#include "rapidjson/error/error.h"
#include "rapidjson/error/en.h"

using namespace std;
using namespace rapidjson;

/**
 * ACLReason constructor:
 * parse input JSON for ACL change reason.
 *
 * JSON should have string attributes 'reason' and 'argument'
 *
 * @param  json		The JSON reason string to parse
 * @throws 		exception ACLReasonMalformed
 */
ACL::ACLReason::ACLReason(const string& json)
{
	Document doc;
	doc.Parse(json.c_str());
	if (doc.HasParseError())
	{
		Logger::getLogger()->error("ACL Reason parse error in %s: %s at %d",
					json.c_str(),
					GetParseError_En(doc.GetParseError()),
							(unsigned)doc.GetErrorOffset());
		throw new ACLReasonMalformed();
	}

	if (!doc.IsObject())
	{
		Logger::getLogger()->error("ACL Reason is not a JSON object: %sd",
					json.c_str());
		throw new ACLReasonMalformed();
	}

	if (doc.HasMember("reason") && doc["reason"].IsString())
	{
		m_reason = doc["reason"].GetString();
	}
	if (doc.HasMember("argument") && doc["argument"].IsString())
	{
		m_argument = doc["argument"].GetString();
	}
}

/**
 * ACL constructor:
 * parse input JSON for ACL content.
 *
 * JSON should have string attributes 'name' and 'service' and 'url' arrays
 *
 * @param  json		The JSON ACL content to parse
 * @throws 		exception ACLMalformed
 */
ACL::ACL(const string& json)
{
	Document doc;
	doc.Parse(json.c_str());
	if (doc.HasParseError())
	{
		Logger::getLogger()->error("ACL parse error in %s: %s at %d",
					json.c_str(),
					GetParseError_En(doc.GetParseError()),
							(unsigned)doc.GetErrorOffset());
		throw new ACLMalformed();
	}
}
