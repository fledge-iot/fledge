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
#include <storage_client.h>

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

	Logger::getLogger()->debug("ACL content is %s", json.c_str());

	if (!doc.HasMember("name"))
	{
		Logger::getLogger()->error("Missing 'name' attribute in ACL JSON data");
		throw new ACLMalformed();
	}
	if (doc.HasMember("name") && doc["name"].IsString())
	{
		m_name = doc["name"].GetString();
	}

	// Check for service array item
	if (doc.HasMember("service") && doc["service"].IsArray())
	{
		auto &items = doc["service"];
		for (auto& item : items.GetArray())
		{
			if (!item.IsObject())
			{
				throw new ACLMalformed();
			}
			for (Value::ConstMemberIterator itr = item.MemberBegin();
							itr != item.MemberEnd();
							++itr)
			{
				// Construct KeyValueItem object
				KeyValueItem i(itr->name.GetString(),
						itr->value.GetString());

				// Add object to the vector
				m_service.push_back(i);
			}
		}
	}

	// Check for url array item
	if (doc.HasMember("url") && doc["url"].IsArray())
	{
		auto &items = doc["url"];
		for (auto& item : items.GetArray())
		{
			if (!item.IsObject())
			{
				throw new ACLMalformed();
			}

			string url = item["url"].GetString();
			Value &acl = item["acl"]; 
			vector<KeyValueItem> v_acl;	

			// Check for acl array
			if (acl.IsArray())
			{
				for (auto& item : acl.GetArray())
				{
					if (!item.IsObject())
					{
						throw new ACLMalformed();
					}
		
					for (Value::ConstMemberIterator itr = item.MemberBegin();
									itr != item.MemberEnd();
									++itr)
					{
						// Construct KeyValueItem object
						KeyValueItem item(itr->name.GetString(),
								itr->value.GetString());

						// Add object to the ACL vector
						v_acl.push_back(item);
					}
				}

			}

			// Construct UrlItem with url and ACL vector
			UrlItem u(url, v_acl);

			// Add object to the URL vector
			m_url.push_back(u);
		}
	}
}
