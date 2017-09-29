#ifndef _LOGGER_H
#define _LOGGER_H
/*
 * FogLAMP storage service.
 *
 * Copyright (c) 2017 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */

#include <string>

/**
 * FogLAMP Logger class used to log to syslog
 *
 * At startup this class should be constructed
 * using the standard constructor. To log a message
 * call debug, info, warn etc. using the instance
 * of the class. TO get that instance call the static
 * method getLogger.
 */
class Logger {
  public:
    Logger(const std::string& application);
    ~Logger();
    static Logger *getLogger();
    void debug(const std::string& msg, ...);
    void info(const std::string& msg, ...);
    void warn(const std::string& msg, ...);
    void error(const std::string& msg, ...);
    void fatal(const std::string& msg, ...);

  private:
    std::string *format(const std::string& msg, va_list ap);
    static Logger   *instance;
};

#endif
