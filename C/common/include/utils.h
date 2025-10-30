#ifndef _FLEDGE_UTILS_H
#define _FLEDGE_UTILS_H
/*
 * Fledge general utilities
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Massimiliano Pinto
 */

#include <string>
#include <algorithm>
#include <vector>

#define _FLEDGE_ROOT_PATH    "/usr/local/fledge"

using namespace std;

/**
 * Return Fledge root dir
 *
 * Return current value of FLEDGE_ROOT env var or
 * default path _FLEDGE_ROOT_PATH
 *
 * @return	Return Fledge root dir
 */
static const string getRootDir()
{
	const char* rootDir = getenv("FLEDGE_ROOT");
	return (rootDir ? string(rootDir) : string(_FLEDGE_ROOT_PATH));
}

/**
 * Return Fledge data dir
 *
 * Return current value of FLEDGE_DATA env var or
 * default value: getRootDir + /data
 *
 * @return	Return Fledge data dir
 */
static const string getDataDir()
{
	const char* dataDir = getenv("FLEDGE_DATA");
	return (dataDir ? string(dataDir) : string(getRootDir() + "/data"));
}

/**
 * @brief Constructs the path for the debug-trace subdirectory in the Fledge data directory.
 *
 * @return A string representing the path to the debug-trace directory.
 */
static std::string getDebugTracePath() 
{
    return getDataDir() + "/logs/debug-trace";
}

/**
 * @brief Converts a string representation of a boolean value to a boolean type.
 *
 * This function takes a string input and checks if it represents a boolean value.
 * It recognizes "true", "1", and their case-insensitive variants as true.
 * Any other string will be interpreted as false.
 *
 * @param str The string to convert to a boolean. Can be "true", "false", "1", "0", etc.
 * @return true if the input string represents a true value; false otherwise.
 *
 * @note This function is case-insensitive and will convert the input string to lowercase
 * before comparison.
 *
 * @example
 * bool result1 = stringToBool("True");    // result1 is true
 * bool result2 = stringToBool("false");   // result2 is false
 * bool result3 = stringToBool("1");       // result3 is true
 * bool result4 = stringToBool("0");       // result4 is false
 */
static bool stringToBool(const std::string& str)
{
    std::string lowerStr = str;
    std::transform(lowerStr.begin(), lowerStr.end(), lowerStr.begin(), ::tolower);
    return (lowerStr == "true" || lowerStr == "1");
}

/** 
 * @brief Validates if a given string is a valid identifier.
 * A valid identifier is defined as a string that does not contain any disallowed characters.
 * 
 * @param str The string to validate as an identifier.
 * @param blockedCharacter A reference to a string that will be set to the first disallowed character found in the input string, if any.
 * @return true if the string is a valid identifier; false otherwise.
*/
static bool isValidIdentifier(const std::string& str, std::string& blockedCharacter)
{
    if (str.empty()) return false;
    // Check for disallowed characters
    static const std::vector<std::string> disallowed_characters = { "\\" };
    for (const auto& ch : disallowed_characters)
    {
        if (str.find(ch) != std::string::npos)
        {
            blockedCharacter = ch;
            return false;
        }
    }
    return true;
}
#endif
