/*
 * Fledge utilities functions for handling JSON document
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Stefano Simonelli, Massimiliano Pinto
 */

#include <iostream>
#include <string>
#include "string_utils.h"
#include <logger.h>

using namespace std;

/**
 * Search and replace a string
 *
 * @param out StringToManage    string in which apply the search and replacement
 * @param     StringToSearch    string to search and replace
 * @param     StringToReplace   substitution string
 *
 */
void StringReplace(std::string& StringToManage,
		   const std::string& StringToSearch,
		   const std::string& StringReplacement)
{
	if (StringToManage.find(StringToSearch) != string::npos)
	{
		StringToManage.replace(StringToManage.find(StringToSearch),
				       StringToSearch.length(),
				       StringReplacement);
	}
}

/**
 * Search and replace all the occurances of a string
 *
 * @param out StringToManage    string in which apply the search and replacement
 * @param     StringToSearch    string to search and replace
 * @param     StringToReplace   substitution string
 *
 */
void StringReplaceAll(std::string& StringToManage,
				   const std::string& StringToSearch,
				   const std::string& StringReplacement)
{

	while (StringToManage.find(StringToSearch) != string::npos)
	{
		StringReplace(StringToManage,StringToSearch, StringReplacement);
	}
}

/**
 * Removes the last level of the hierarchy
 *
 */
std::string evaluateParentPath(const std::string& path, char separator)
{
	std::string parent;

	parent = path;
	if (parent.length() > 1)
	{
		if (parent.find(separator) != string::npos)
		{
			while (parent.back() != separator)
			{
				parent.erase(parent.size() - 1);
			}
			if (parent.back() == separator)
			{
				parent.erase(parent.size() - 1);
			}
		}
	}

	return parent;
}

/**
 * Extract last level of the hierarchy
 *
 */
std::string extractLastLevel(const std::string& path, char separator)
{
	std::string level;
	std::string tmpPath;
	char end_char;

	tmpPath = path;

	if (tmpPath.length() > 1)
	{
		if (tmpPath.find(separator) != string::npos)
		{
			end_char = tmpPath.back();
			while (end_char != separator)
			{
				level.insert(0, 1, end_char);
				tmpPath.erase(tmpPath.size() - 1);
				end_char = tmpPath.back();
			}
		}
		else
		{
			level = path;
		}
	}

	return level;
}



/**
 * Removes slash when not needed, at the beggining and at the end,
 * substitutes // with /
 *
 * @param     stringToFix    string to handle
 *
 */
std::string StringSlashFix(const std::string& stringToFix)
{
	std::string stringFixed;

	stringFixed = stringToFix;

	if (!stringFixed.empty()) {

		char singleChar;

		// Remove first char if '/'
		for (singleChar = stringFixed.front() ; singleChar == '/' ; singleChar = stringFixed.front())
		{
			stringFixed.erase(0, 1);
		}

		// Remove last char if '/'
		for (singleChar = stringFixed.back() ; singleChar == '/' ; singleChar = stringFixed.back())
		{
			stringFixed.pop_back();
		}

		// Substitute // with /
		while (stringFixed.find("//") != string::npos)
		{
			StringReplace(stringFixed, "//", "/");
		}
	}

	return stringFixed;
}

/**
 * Strips Line feed and carige return
 *
 */
void StringStripCRLF(std::string& StringToManage)
{
	string::size_type pos = 0;

	pos = StringToManage.find ('\r',pos);
	if (pos != string::npos )
	{
		StringToManage.erase ( pos, 2 );
	}

	pos = StringToManage.find ('\n',pos);
	if (pos != string::npos )
	{
		StringToManage.erase ( pos, 2 );
	}

}

/**
 * URL-encode a given string
 *
 * @param s             Input string that is to be URL-encoded
 * @return              URL-encoded output string
 */
string urlEncode(const string &s)
{
	ostringstream escaped;
	escaped.fill('0');
	escaped << hex;

	for (string::const_iterator i = s.begin(), n = s.end();
				    i != n;
				    ++i)
	{
		string::value_type c = (*i);

		// Keep alphanumeric and other accepted characters intact
		if (isalnum(c) || c == '-' || c == '_' || c == '.' || c == '~') {
			escaped << c;
			continue;
		}

		 // Any other characters are percent-encoded
		escaped << uppercase;
		escaped << '%' << setw(2) << int((unsigned char) c);
		escaped << nouppercase;
	}

	return escaped.str();
}

/**
 * Check if a char is an hex value
 *
 * @param c	The input char
 * @return	True with hex value
 * 		false otherwise
 */
static inline bool ishex (const char c)
{
	if (isdigit(c) ||
	    c=='A' ||
	    c=='B' ||
	    c=='C' ||
	    c=='D' ||
	    c=='E' ||
	    c=='F')
	{
		return true;
	}
	else
	{
		return false;
	}
}

/**
 * URL decode of a given string
 *
 * @param name	The string to decode
 * @return	The URL decoded string
 *
 * In case of decoding errors the routine returns
 * current decoded string
 */
string urlDecode(const std::string& name)
{
	std::string decoded(name);
	char* s = (char *)name.c_str();
	char* dec = (char *)decoded.c_str();
	char* o;
	const char* end = s + name.length();
	int c;

	for (o = dec; s <= end; o++)
	{
		c = *s++;
		if (c == '+')
		{
			c = ' ';
		}
		else if (c == '%' && (!ishex(*s++) ||
			 !ishex(*s++) ||
			 !sscanf(s - 2, "%2x", &c)))
		{
			break;
		}

		if (dec)
		{
			*o = c;
		}
	}

	return string(dec);
}

/**
 * Escape all double quotes characters in the string
 *
 * @param str	The string to escape
 */
void StringEscapeQuotes(std::string& str)
{
	for (size_t i = 0; i < str.length(); i++)
	{
		Logger::getLogger()->fatal("becomes '%s'", str.c_str());
		if (str[i] == '\"' && (i == 0 || str[i-1] != '\\'))
		{
			str.replace(i, 1, "\\\"");
		}

	}
}
