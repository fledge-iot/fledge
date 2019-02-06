/*
 * FogLAMP storage service.
 *
 * Copyright (c) 2017-2018 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch, Massimiliano Pinto
 */
#include <logger.h>
#include <stdio.h>
#include <unistd.h>
#include <syslog.h>
#include <stdarg.h>
#include <memory>
#include <string.h>
#include <sys/time.h>

using namespace std;

// uncomment line below to get uSec level timestamps
//#define ADD_USEC_TS

inline long getCurrTimeUsec()
{
	struct timeval m_timestamp;
	gettimeofday(&m_timestamp, NULL);
	return m_timestamp.tv_usec;
}

Logger *Logger::instance = 0;

Logger::Logger(const string& application)
{
	m_app_name = new string(application);
	openlog(m_app_name->c_str(), LOG_PID|LOG_CONS, LOG_USER);
	instance = this;
}

Logger::~Logger()
{
	closelog();
	delete m_app_name;
}

Logger *Logger::getLogger()
{
	return instance;
}

/**
 *  Set the minimum logging level to report for this process.
 *
 *  @param level	Sring representing level
 */
void Logger::setMinLevel(const string& level)
{
	if (level.compare("info") == 0)
	{
		setlogmask(LOG_UPTO(LOG_INFO));
	} else if (level.compare("warning") == 0)
	{
		setlogmask(LOG_UPTO(LOG_WARNING));
	} else if (level.compare("debug") == 0)
	{
		setlogmask(LOG_UPTO(LOG_DEBUG));
	} else if (level.compare("error") == 0)
	{
		setlogmask(LOG_UPTO(LOG_ERR));
	} else
	{
		error("Request to set unsupported log level %s", level.c_str());
	}
}

void Logger::debug(const string& msg, ...)
{
	va_list args;
	va_start(args, msg);
	string *fmt = format(msg, args);
	syslog(LOG_DEBUG, "DEBUG: %s", fmt->c_str());
	delete fmt;
	va_end(args);
}

void Logger::info(const string& msg, ...)
{
	va_list args;
	va_start(args, msg);
	string *fmt = format(msg, args);
#ifdef ADD_USEC_TS
	syslog(LOG_INFO, "[.%06ld] INFO: %s", getCurrTimeUsec(), fmt->c_str());
#else
	syslog(LOG_INFO, "INFO: %s", fmt->c_str());
#endif
	delete fmt;
	va_end(args);
}

void Logger::warn(const string& msg, ...)
{
	va_list args;
	va_start(args, msg);
	string *fmt = format(msg, args);
	syslog(LOG_WARNING, "WARNING: %s", fmt->c_str());
	delete fmt;
	va_end(args);
}

void Logger::error(const string& msg, ...)
{
	va_list args;
	va_start(args, msg);
	string *fmt = format(msg, args);
	syslog(LOG_ERR, "ERROR: %s", fmt->c_str());
	delete fmt;
	va_end(args);
}

void Logger::fatal(const string& msg, ...)
{
	va_list args;
	va_start(args, msg);
	string *fmt = format(msg, args);
	syslog(LOG_CRIT, "FATAL: %s", fmt->c_str());
	delete fmt;
	va_end(args);
}

string *Logger::format( const std::string& format, va_list args)
{
char	buf[1000];

	  vsnprintf(buf, sizeof(buf), format.c_str(), args);
	  return new string(buf);
}
