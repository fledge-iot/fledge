#ifndef _LOG_UTILS_H
#define _LOG_UTILS_H
/*
 * Log utility functions
 *
 * Copyright (c) 2017-2018 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch, Massimiliano Pinto
 */

#include <string>
#include <logger.h>

namespace LogUtils {
    /*
     * Log helper functions that will log both in the Fledge syslog file and in stdout for unit tests
     */

    template<class... Args>
    void log_debug(const std::string& format, Args&&... args) {  
        #ifdef UNIT_TEST
        printf(std::string(format).append("\n").c_str(), std::forward<Args>(args)...);
        fflush(stdout);
        #endif
        Logger::getLogger()->debug(format.c_str(), std::forward<Args>(args)...);
    }

    template<class... Args>
    void log_info(const std::string& format, Args&&... args) {    
        #ifdef UNIT_TEST
        printf(std::string(format).append("\n").c_str(), std::forward<Args>(args)...);
        fflush(stdout);
        #endif
        Logger::getLogger()->info(format.c_str(), std::forward<Args>(args)...);
    }

    template<class... Args>
    void log_warn(const std::string& format, Args&&... args) { 
        #ifdef UNIT_TEST  
        printf(std::string(format).append("\n").c_str(), std::forward<Args>(args)...);
        fflush(stdout);
        #endif
        Logger::getLogger()->warn(format.c_str(), std::forward<Args>(args)...);
    }

    template<class... Args>
    void log_error(const std::string& format, Args&&... args) {   
        #ifdef UNIT_TEST
        printf(std::string(format).append("\n").c_str(), std::forward<Args>(args)...);
        fflush(stdout);
        #endif
        Logger::getLogger()->error(format.c_str(), std::forward<Args>(args)...);
    }

    template<class... Args>
    void log_fatal(const std::string& format, Args&&... args) {  
        #ifdef UNIT_TEST
        printf(std::string(format).append("\n").c_str(), std::forward<Args>(args)...);
        fflush(stdout);
        #endif
        Logger::getLogger()->fatal(format.c_str(), std::forward<Args>(args)...);
    }
}

#endif /* _LOG_UTILS_H */
