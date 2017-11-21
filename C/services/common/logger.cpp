/*
 * FogLAMP storage service.
 *
 * Copyright (c) 2017 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <logger.h>
#include <stdio.h>
#include <unistd.h>
#include <syslog.h>
#include <stdarg.h>
#include <memory>

using namespace std;

Logger *Logger::instance = 0;

Logger::Logger(const string& application)
{
	openlog(application.c_str(), LOG_PID|LOG_CONS, LOG_USER);
	instance = this;
}

Logger::~Logger()
{
	closelog();
}

Logger *Logger::getLogger()
{
	return instance;
}

void Logger::debug(const string& msg, ...)
{
	va_list args;
	va_start(args, msg);
	string *fmt = format(msg, args);
	syslog(LOG_DEBUG, "%s", fmt->c_str());
	delete fmt;
	va_end(args);
}

void Logger::info(const string& msg, ...)
{
	va_list args;
	va_start(args, msg);
	string *fmt = format(msg, args);
	syslog(LOG_INFO, "%s", fmt->c_str());
	delete fmt;
	va_end(args);
}

void Logger::warn(const string& msg, ...)
{
	va_list args;
	va_start(args, msg);
	string *fmt = format(msg, args);
	syslog(LOG_WARNING, "%s", fmt->c_str());
	delete fmt;
	va_end(args);
}

void Logger::error(const string& msg, ...)
{
	va_list args;
	va_start(args, msg);
	string *fmt = format(msg, args);
	syslog(LOG_ERR, "%s", fmt->c_str());
	delete fmt;
	va_end(args);
}

void Logger::fatal(const string& msg, ...)
{
	va_list args;
	va_start(args, msg);
	string *fmt = format(msg, args);
	syslog(LOG_CRIT, "%s", fmt->c_str());
	delete fmt;
	va_end(args);
}

string *Logger::format( const std::string& format, va_list args)
{
char	buf[1000];

	  vsnprintf(buf, sizeof(buf), format.c_str(), args);
	  return new string(buf);
}
