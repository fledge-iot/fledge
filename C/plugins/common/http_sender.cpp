/*
 * Fledge HTTP Sender wrapper.
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Massimiliano Pinto, Mark Riddoch
 */

#include <http_sender.h>
#include <unistd.h>
#include <string_utils.h>
#include <sstream>   // for std::stringstream
#include <fstream> 
#include <logger.h>

using namespace std;

/**
 * Constructor
 */
HttpSender::HttpSender()
{
}

/**
 * Destructor
 */
HttpSender::~HttpSender()
{
}

/**
 * @brief Constructs the file path for the OMF log based on environment variables.
 *
 * This function checks for the existence of two environment variables:
 * FLEDGE_DATA and FLEDGE_ROOT. It constructs the file path to the OMF log
 * file accordingly. The priority is given to FLEDGE_DATA. If neither
 * environment variable is set, an error message is printed, and an empty
 * string is returned.
 *
 * @return A string representing the path to the OMF log file, or an empty
 *         string if neither environment variable is set.
 */
std::string HttpSender::getOMFTracePath() 
{
    const char* fledgeData = getenv("FLEDGE_DATA");
    const char* fledgeRoot = getenv("FLEDGE_ROOT");
    std::stringstream pathStream;

    if (fledgeData) 
    {
        pathStream << fledgeData << "/debug-trace/omf.log"; // Construct path using FLEDGE_DATA
    } 
    else if (fledgeRoot)
    {
        pathStream << fledgeRoot << "/data/debug-trace/omf.log"; // Construct path using FLEDGE_ROOT
    } 
    else 
    {
        return ""; // Return an empty string to indicate an error
    }

    return pathStream.str(); // Return the constructed file path as a string
}