/*
 * Fledge OSI Soft OMF interface to PI Server.
 *
 * Copyright (c) 2020 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */

#include <utility>
#include <iostream>
#include <string>
#include <cstring>
#include <omf.h>
#include <OMFHint.h>
#include <logger.h>
#include <rapidjson/document.h>
#include "rapidjson/error/en.h"
#include "string_utils.h"
#include <string_utils.h>
#include <datapoint.h>

using namespace std;
using namespace rapidjson;

OMFHints::OMFHints(const string& hints)
{
	string hintsTmp;

	hintsTmp = hints;
	StringReplaceAll(hintsTmp,"\\","");

	m_chksum = 0;
	if (hintsTmp[0] == '\"')
	{
		// Skip any enclosing "'s
		m_doc.Parse(hintsTmp.substr(1, hintsTmp.length() - 2).c_str());
		for (int i = 1; i < hintsTmp.length() - 1; i++)
			m_chksum += hintsTmp[i];
	}
	else
	{
		m_doc.Parse(hintsTmp.c_str());
		for (int i = 0; i < hintsTmp.length(); i++)
			m_chksum += hintsTmp[i];
	}


	//# FIXME_I
	Logger::getLogger()->setMinLevel("debug");
	Logger::getLogger()->debug("xxx3 %s - hintsTmp :%s: m_chksum :%H: ", __FUNCTION__, hintsTmp.c_str(), m_chksum);
	Logger::getLogger()->setMinLevel("warning");

	if (m_doc.HasParseError())
	{
		Logger::getLogger()->error("Ignoring OMFHint '%s' parse error in JSON", hintsTmp.c_str());
	}
	else
	{
		for (Value::ConstMemberIterator itr = m_doc.MemberBegin();
					itr != m_doc.MemberEnd(); ++itr)
		{
			const char *name = itr->name.GetString();
			if (strcmp(name, "number") == 0)
			{
				m_hints.push_back(new OMFNumberHint(itr->value.GetString()));
			}
			else if (strcmp(name, "integer") == 0)
			{
				m_hints.push_back(new OMFIntegerHint(itr->value.GetString()));
			}
			else if (strcmp(name, "typeName") == 0)
			{
				m_hints.push_back(new OMFTypeNameHint(itr->value.GetString()));
			}
			else if (strcmp(name, "tagName") == 0)
			{
				m_hints.push_back(new OMFTagNameHint(itr->value.GetString()));
			}
			else if (strcmp(name, "tag") == 0)
			{
				m_hints.push_back(new OMFTagHint(itr->value.GetString()));
			}
			else if (strcmp(name, "AFLocation") == 0)
			{
				m_hints.push_back(new OMFAFLocationHint(itr->value.GetString()));
			}
			else if (strcmp(name, "datapoint") == 0)
			{
				const Value &child = itr->value;
				if (child.IsArray())
				{
					for (Value::ConstValueIterator dpitr2 = child.Begin(); dpitr2 != child.End(); ++dpitr2)
					{
						if (dpitr2->HasMember("name"))
						{
							const string dpname = (*dpitr2)["name"].GetString();
							vector<OMFHint *> hints;
							for (Value::ConstMemberIterator dpitr = dpitr2->MemberBegin(); dpitr != dpitr2->MemberEnd(); ++dpitr)
							{
								const char *name = dpitr->name.GetString();
								if (strcmp(name, "number") == 0)
								{
									hints.push_back(new OMFNumberHint(dpitr->value.GetString()));
								}
								else if (strcmp(name, "integer") == 0)
								{
									hints.push_back(new OMFIntegerHint(dpitr->value.GetString()));
								}
								else if (strcmp(name, "typeName") == 0)
								{
									hints.push_back(new OMFTypeNameHint(dpitr->value.GetString()));
								}
								else if (strcmp(name, "tagName") == 0)
								{
									hints.push_back(new OMFTagNameHint(dpitr->value.GetString()));
								}
								else if (strcmp(name, "tag") == 0)
								{
									hints.push_back(new OMFTagHint(dpitr->value.GetString()));
								}
							}
							m_datapointHints.insert(std::pair<string,vector<OMFHint *>>(dpname, hints));
						}
					}

				}
				else
				{
					if (child.HasMember("name"))
					{
						const string dpname = child["name"].GetString();
						vector<OMFHint *> hints;
						for (Value::ConstMemberIterator dpitr = child.MemberBegin(); dpitr != child.MemberEnd(); ++dpitr)
						{
							const char *name = dpitr->name.GetString();
							if (strcmp(name, "number") == 0)
							{
								hints.push_back(new OMFNumberHint(dpitr->value.GetString()));
							}
							else if (strcmp(name, "integer") == 0)
							{
								hints.push_back(new OMFIntegerHint(dpitr->value.GetString()));
							}
							else if (strcmp(name, "typeName") == 0)
							{
								hints.push_back(new OMFTypeNameHint(dpitr->value.GetString()));
							}
							else if (strcmp(name, "tagName") == 0)
							{
								hints.push_back(new OMFTagNameHint(dpitr->value.GetString()));
							}
							else if (strcmp(name, "tag") == 0)
							{
								hints.push_back(new OMFTagHint(dpitr->value.GetString()));
							}
						}
						m_datapointHints.insert(std::pair<string,vector<OMFHint *>>(dpname, hints));
					}
				}
			}
			else
			{
				Logger::getLogger()->error("Unrecognised hint '%s' in OMFHint", name);
			}
		}
	}

}

/**
 * Destructor for Hints class
 */
OMFHints::~OMFHints()
{
	for (OMFHint *hint : m_hints)
	{
		delete hint;
	}
	for (auto it = m_datapointHints.begin(); it != m_datapointHints.end(); it++)
	{
		for (OMFHint *hint : it->second)
		{
			delete hint;
		}
	}
	m_datapointHints.erase(m_datapointHints.begin(), m_datapointHints.end());
	m_hints.clear();
}

/**
 * Return the hints for a given data point. If it has known then return the hits
 * for all data points.
 *
 * @param datapoint The name of the datapoint to retrieve the hints for
 */
const vector<OMFHint *>& OMFHints::getHints(const string& datapoint) const
{
	auto it = m_datapointHints.find(datapoint);
	if (it != m_datapointHints.end())
	{
		return it->second;
	}
	return m_hints;
}
