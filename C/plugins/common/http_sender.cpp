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
#include <utils.h>
#include <sys/stat.h>
#include <sys/types.h>

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
 * @brief Creates the "debug-trace" directory under the base directory returned by getDataDir().
 * 
 * This function ensures that the "debug-trace" directory is created only if the base directory exists
 */
bool HttpSender::createDebugTraceDirectory() 
{
    // Step 1: Retrieve the base data directory
    std::string baseDir = getDataDir(); 
    std::string debugTraceDir = baseDir + "/debug-trace";

    // Step 2: Check if the base directory exists
    struct stat baseInfo;
    if (stat(baseDir.c_str(), &baseInfo) == 0 && (baseInfo.st_mode & S_IFDIR))
    {
        // Base directory exists, proceed to creating the debug-trace directory

        // Step 3: Check if the debug-trace directory exists
        struct stat debugTraceInfo;
        if (stat(debugTraceDir.c_str(), &debugTraceInfo) != 0) 
        {
            // debug-trace directory does not exist; attempt to create it
            if (mkdir(debugTraceDir.c_str(), 0755) == 0) 
            {
                Logger::getLogger()->info("Successfully created 'debug-trace' directory at: %s", debugTraceDir.c_str());
                return true;
            } 
            else
            {
                Logger::getLogger()->error("Failed to create 'debug-trace' directory at: %s. Please check permissions.", debugTraceDir.c_str());
                return false;
            }
        } 
        else if (debugTraceInfo.st_mode & S_IFDIR)
        {
            // debug-trace directory already exists
            Logger::getLogger()->info("'debug-trace' directory already exists at: %s", debugTraceDir.c_str());
            return true;
        } 
        else 
        {
            // Path exists but is not a directory
            Logger::getLogger()->error("Path exists but is not a directory: %s", debugTraceDir.c_str());
            return false;
        }
    } 
    
    // Base directory does not exist
    Logger::getLogger()->warn("Base directory does not exist: %s. 'debug-trace' directory will not be created.", baseDir.c_str());
    return false;
}

/**
 * @brief Constructs the file path for the OMF trace based on environment variables.
 *
 * @return A string representing the path to the OMF trace file, or an empty
 *         string if neither environment variable is set.
 */
std::string HttpSender::getOMFTracePath() 
{
    return getDataDir() + "/debug-trace/omf.log";
}