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

#define OMFHINTS_AFLOCATION "\"AFLocation\""


/**
 *  Extracts from a complete OMF hint the part on which the checksum should be generated,
 *  for example, it will remove the section related to the AFLocation hint to avoid the creation of a new type
 *  when the value changes.
 *
 * @param hint   Original/complete OMF hint
 *
 * @return       OMF hint that should be considered for the calculation of the checksum
 */
string OMFHints::getHintForChecksum(const string &hint) {

	size_t pos1, pos2, pos3;
	string hintFinal;

	hintFinal = hint;

	pos1 = hintFinal.find(OMFHINTS_AFLOCATION);
	if (pos1 != std::string::npos)
	{
		pos2 = hintFinal.find(",", pos1);
		if (pos2 != std::string::npos)
		{
			// There is another hint
			hintFinal.erase(pos1, pos2 - pos1 + 1);
		} else {
			pos3 = hintFinal.find(",");
			if (pos3 != std::string::npos)
			{
				hintFinal.erase(pos3, hintFinal.length() - pos3 -1);
			}else {
				hintFinal.erase(pos1, hintFinal.length() - pos1 -1);
			}
		}
	}

	// Handle special cases
	StringReplace(hintFinal, "{}", "");

	if (hintFinal.length() == 3) {

		StringReplace(hintFinal, "{", "");
		StringReplace(hintFinal, "}", "");
	}

	return (hintFinal);
}

/**
 *  Decodes the OMFhint in JSON format assigning the values to the memory structures: m_chksum,  m_hints and m_datapointHints
 *
 * @param hint   OMF hint in JSON format
 */
OMFHints::OMFHints(const string& hints)
{
	string hintsTmp, hintsChksum;

	hintsTmp = hints;
	StringReplaceAll(hintsTmp,"\\","");

	m_chksum = 0;
	if (hintsTmp[0] == '\"')
	{
		// Skip any enclosing "'s
		m_doc.Parse(hintsTmp.substr(1, hintsTmp.length() - 2).c_str());
		hintsChksum = getHintForChecksum(hintsTmp);
		for (int i = 1; i < hintsChksum.length() - 1; i++)
			m_chksum += hintsChksum[i];
	}
	else
	{
		m_doc.Parse(hintsTmp.c_str());
		hintsChksum = getHintForChecksum(hintsTmp);
		for (int i = 0; i < hintsChksum.length(); i++)
			m_chksum += hintsChksum[i];
	}
	Logger::getLogger()->debug("%s - hints original :%s: adapted :%s: chksum :%X: "
		, __FUNCTION__
		,hints.c_str()
		,hintsChksum.c_str()
		, m_chksum);

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
			else if (strcmp(name, "LegacyType") == 0)
			{
				m_hints.push_back(new OMFLegacyTypeHint(itr->value.GetString()));
			}
			else if (strcmp(name, "source") == 0)
			{
				m_hints.push_back(new OMFSourceHint(itr->value.GetString()));
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
								else if (strcmp(name, "uom") == 0)
								{
									hints.push_back(new OMFUOMHint(dpitr->value.GetString()));
								}
								else if (strcmp(name, "source") == 0)
								{
									hints.push_back(new OMFSourceHint(dpitr->value.GetString()));
								}
								else if (strcmp(name, "minimum") == 0)
								{
									hints.push_back(new OMFMinimumHint(dpitr->value.GetString()));
								}
								else if (strcmp(name, "maximum") == 0)
								{
									hints.push_back(new OMFMaximumHint(dpitr->value.GetString()));
								}
								else if (strcmp(name, "interpolation") == 0)
								{
									string interpolation = dpitr->value.GetString();
									if (interpolation.compare("continuous")
											&& interpolation.compare("discrete")
										       && interpolation.compare("stepwisecontinuousleading")
										       && interpolation.compare("stepwisecontinuousfollowing"))
									{
										Logger::getLogger()->warn("Invalid value for interpolation hint for %s, only continuous, discrete, stepwisecontinuousleading, and stepwisecontinuousfollowing are supported", dpname.c_str());
									}
									else
									{
										hints.push_back(new OMFInterpolationHint(interpolation));
									}
								}
								else if (strcmp(name, "name"))	// Ignore the name
								{
									Logger::getLogger()->warn("Invalid OMF hint '%s'", name);
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
							else if (strcmp(name, "uom") == 0)
							{
								hints.push_back(new OMFUOMHint(dpitr->value.GetString()));
							}
							else if (strcmp(name, "source") == 0)
							{
								hints.push_back(new OMFSourceHint(dpitr->value.GetString()));
							}
							else if (strcmp(name, "minimum") == 0)
							{
								hints.push_back(new OMFMinimumHint(dpitr->value.GetString()));
							}
							else if (strcmp(name, "maximum") == 0)
							{
								hints.push_back(new OMFMaximumHint(dpitr->value.GetString()));
							}
							else if (strcmp(name, "interpolation") == 0)
							{
								string interpolation = dpitr->value.GetString();
								if (interpolation.compare("continuous")
										&& interpolation.compare("discrete")
									       && interpolation.compare("stepwisecontinuousleading")
									       && interpolation.compare("stepwisecontinuousfollowing"))
								{
									Logger::getLogger()->warn("Invalid value for interpolation hint for %s, only continuous, discrete, stepwisecontinuousleading, and stepwisecontinuousfollowing are supported", dpname.c_str());
								}
								else
								{
									hints.push_back(new OMFInterpolationHint(interpolation));
								}
							}
							else if (strcmp(name, "name"))	// Ignore the name
							{
								Logger::getLogger()->warn("Invalid OMF hint '%s'", name);
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
