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
#include "string_utils.h"

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