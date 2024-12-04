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
 * @brief Creates the '/logs/debug-trace' directory under the directory returned by getDataDir().
 * 
 * This function ensures that both the 'logs' directory and the 'debug-trace' directory are created if they do not exist.
 */
bool HttpSender::createDebugTraceDirectory() 
{
    // Retrieve the 'logs' and 'debug-trace' directory paths
    std::string logsDir = getDataDir() + "/logs";
    std::string debugTraceDir = logsDir + "/debug-trace";

    // Ensure path consistency with getDebugTracePath(). Assert is commented out to prevent unexpected runtime interruptions in execution
    // std::assert(debugTraceDir == getDebugTracePath()); 

    auto createDir = [](const std::string& dirPath) -> bool 
    {
        struct stat dirInfo;
        if (stat(dirPath.c_str(), &dirInfo) == 0)
        {
            if (dirInfo.st_mode & S_IFDIR)
            {
                return true; // Directory exists
            }
            else
            {
                Logger::getLogger()->error("Path exists but is not a directory: %s", dirPath.c_str());
                return false;
            }
        }
        else
        {
            // Directory does not exist, attempt to create it
            if (mkdir(dirPath.c_str(), 0755) == 0)
            {
                return true; // Success
            }
            else
            {
                return false;
            }
        }
    };

    // Create the logs directory if it does not exist
    if (!createDir(logsDir))
    {
        Logger::getLogger()->error("Failed to create directory: %s. 'debug-trace' directory will not be created.", logsDir.c_str());
        return false;
    }

    // Create the debug-trace directory if it does not exist
    if (!createDir(debugTraceDir))
    {
        Logger::getLogger()->error("Failed to create 'debug-trace' directory: %s.", debugTraceDir.c_str());
        return false;
    }

    return true; 
}

/**
 * @brief Constructs the file path for the OMF log.
 *
 * @return A string representing the path to the OMF log file.
 */
std::string HttpSender::getOMFTracePath() 
{
    return getDebugTracePath() + "/omf.log";
}
