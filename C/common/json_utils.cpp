/*
 * Fledge utilities functions for handling JSON document
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Stefano Simonelli
 */

#include <iostream>
#include <string>
#include <vector>
#include "json_utils.h"
#include "rapidjson/document.h"

using namespace std;
using namespace rapidjson;

/**
 * Processes a string containing an array in JSON format and loads a vector of string
 *
 * @param vectorString  vector of string used by reference in which the JSON array will be loaded
 * @param JSONString    string containing an array in JSON format
 * @param Key           key of the JSON from which the array should be evaluated
 *
 */
bool JSONStringToVectorString(std::vector<std::string>& vectorString,
			      const std::string& JSONString,
			      const std::string& Key)
{
	bool success = true;

	Document JSONdoc;

	JSONdoc.Parse(JSONString.c_str());


	if (JSONdoc.HasParseError())
	{
		success = false;

	} else if (!JSONdoc.HasMember(Key.c_str()))
	{
		success = false;

	} else if (!JSONdoc[Key.c_str()].IsArray())
	{

		success = false;
	}

	if (success)
	{
		const Value &filterList = JSONdoc[Key.c_str()];
		if (!filterList.Size())
		{
			success = false;
		} else
		{
			for (Value::ConstValueIterator itr = filterList.Begin();
			     itr != filterList.End(); ++itr)
			{
				vectorString.emplace_back(itr->GetString());
			}

		}
	}

	return success;
}

string JSONescape(const std::string& subject)
{
	string escaped;
	escaped.reserve(subject.size());

	for (char c : subject)
	{
		switch (c)
		{
			case '\\':
				escaped += "\\\\";
				break;
			case '"':
				escaped += "\\\"";
				break;
			case '\n':
				escaped += "\\n";
				break;
			case '\r':
				escaped += "\\r";
				break;
			case '\t':
				escaped += "\\t";
				break;
			case '\b':
				escaped += "\\b";
				break;
			case '\f':
				escaped += "\\f";
				break;
			default:
				escaped += c;
				break;
		}
	}
	return escaped;
}

/**
 * Return unescaped version of a JSON string
 *
 * Routine removes leading and trailing " and processes the
 * standard JSON escape sequences: \\ \" \n \r \t \b \f.
 * Unicode escapes (\uXXXX) and any unrecognised sequences are
 * copied through unchanged so that JSON text held in the string
 * can be parsed downstream.
 *
 * This is the inverse of JSONescape and of the escaping applied
 * by the rapidjson Writer.
 *
 * @param input         Input string
 * @return              Unescaped string
 */
std::string JSONunescape(const std::string& input)
{
	std::string output;
	size_t inputSize = input.size();
	output.reserve(inputSize);

	for (size_t i = 0; i < inputSize; ++i)
	{
		// skip leading or trailing "
		if ((i == 0 || i == inputSize -1) && input[i] == '"')
		{
			continue;
		}

		if (input[i] == '\\' && i + 1 < inputSize)
		{
			switch (input[i + 1])
			{
				case '\\':
					output.push_back('\\');
					++i;
					break;
				case '"':
					output.push_back('"');
					++i;
					break;
				case 'n':
					output.push_back('\n');
					++i;
					break;
				case 'r':
					output.push_back('\r');
					++i;
					break;
				case 't':
					output.push_back('\t');
					++i;
					break;
				case 'b':
					output.push_back('\b');
					++i;
					break;
				case 'f':
					output.push_back('\f');
					++i;
					break;
				default:
					// Unrecognised escape (e.g. \uXXXX):
					// copy the backslash through unchanged
					output.push_back(input[i]);
					break;
			}
		}
		else
		{
			output.push_back(input[i]);
		}
	}

	return output;
}
