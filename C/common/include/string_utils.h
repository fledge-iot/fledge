#ifndef _STRING_UTILS_H
#define _STRING_UTILS_H
/*
 * Fledge utilities functions for handling stringa
 *
 * Copyright (c) 2019 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Stefano Simonelli, Massimiliano Pinto
 */

#include <string>
#include <sstream>
#include <iomanip>

using namespace std;

void StringReplace(std::string& StringToManage,
		   const std::string& StringToSearch,
		   const std::string& StringReplacement);

void StringReplaceAll(std::string& StringToManage,
					  const std::string& StringToSearch,
					  const std::string& StringReplacement);

string StringSlashFix(const string& stringToFix);
std::string evaluateParentPath(const std::string& path, char separator);
std::string extractLastLevel(const std::string& path, char separator);

void   StringStripCRLF(std::string& StringToManage);
string StringStripWhiteSpacesAll(const std::string& original);
string StringStripWhiteSpacesExtra(const  std::string& original);
void StringStripQuotes(std::string& StringToManage);

string urlEncode(const string& s);
string urlDecode(const string& s);
void StringEscapeQuotes(string& s);

char *trim(char *str);
std::string StringLTrim(const std::string& str);
std::string StringRTrim(const std::string& str);
std::string StringTrim(const std::string& str);

bool IsRegex(const string &str);


#endif
