/*
 * Fledge storage service.
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
#include <future>
#include <algorithm>

using namespace std;

// uncomment line below to get uSec level timestamps
// #define ADD_USEC_TS

inline long getCurrTimeUsec()
{
	struct timeval m_timestamp;
	gettimeofday(&m_timestamp, NULL);
	return m_timestamp.tv_usec;
}

Logger *Logger::instance = 0;

Logger::Logger(const string& application)
{
static char ident[80];

	/* Prepend "Fledge " in all cases other than Fledge itself and Fledge Storage.
	 */
	if (application.compare("Fledge") != 0 && application.compare("Fledge Storage") != 0)
	{
		snprintf(ident, sizeof(ident), "Fledge %s", application.c_str());
	}
	else
	{
		strncpy(ident, application.c_str(), sizeof(ident));
	}
	openlog(ident, LOG_PID|LOG_CONS, LOG_USER);
	instance = this;
	m_level = LOG_WARNING;
	m_interceptors = std::make_shared<InterceptorMap>(); // Initialize with empty map
}

Logger::~Logger()
{
	closelog();
	// Stop the getLogger() call returning a deleted instance
	if (instance == this)
		instance = NULL;

	// Clean up finished futures
	while (!m_futures.empty())
	{
		cleanupFutures();
	}
}

Logger *Logger::getLogger()
{
	if (!instance)
		instance = new Logger("fledge");

	return instance;
}

void Logger::setMinLevel(const string& level)
{
	if (level.compare("info") == 0)
	{
		setlogmask(LOG_UPTO(LOG_INFO));
		levelString = level;
		m_level = LOG_INFO;
	} else if (level.compare("warning") == 0)
	{
		setlogmask(LOG_UPTO(LOG_WARNING));
		levelString = level;
		m_level = LOG_WARNING;
	} else if (level.compare("debug") == 0)
	{
		setlogmask(LOG_UPTO(LOG_DEBUG));
		levelString = level;
		m_level = LOG_DEBUG;
	} else if (level.compare("error") == 0)
	{
		setlogmask(LOG_UPTO(LOG_ERR));
		levelString = level;
		m_level = LOG_ERR;
	} else
	{
		error("Request to set unsupported log level %s", level.c_str());
	}
}

bool Logger::registerInterceptor(LogLevel level, LogInterceptor callback, void* userData)
{
	std::lock_guard<std::mutex> lock(m_interceptorMapMutex);
	auto newMap = std::make_shared<InterceptorMap>(*m_interceptors); // Copy current map
	auto it = newMap->emplace(level, LogInterceptorNode{callback, userData}); // Add new interceptor
	if (it != newMap->end())
	{
		m_interceptors = newMap; // Update the shared_ptr
		return true;
	}
	return false;
}

bool Logger::unregisterInterceptor(LogLevel level, LogInterceptor callback)
{
	std::lock_guard<std::mutex> lock(m_interceptorMapMutex);
	auto newMap = std::make_shared<InterceptorMap>(*m_interceptors); // Copy current map
	auto range = newMap->equal_range(level);
	for (auto it = range.first; it != range.second; ++it)
	{
		if (it->second.callback == callback)
		{
			newMap->erase(it); // Remove the interceptor
			m_interceptors = newMap; // Update the shared_ptr
			return true; // Remove only one matching entry
		}
	}
	return false;
}

void Logger::executeInterceptor(LogLevel level, const std::string& message)
{
	std::shared_ptr<InterceptorMap> interceptors;
	{
		std::lock_guard<std::mutex> lock(m_interceptorMapMutex);
		interceptors = m_interceptors; // Get a consistent snapshot of the interceptor map
	}

	auto range = interceptors->equal_range(level);
	for (auto it = range.first; it != range.second; ++it)
	{
		// Offload the callback execution to a separate thread using std::async
		m_futures.emplace_back(std::async(std::launch::async, [it, level, message]() {
			it->second.callback(level, message, it->second.userData);
		}));
	}

	// Clean up finished futures
	if (m_futures.size() >= m_futuresCountLimit)
	{
		cleanupFutures();
	}
}

void Logger::cleanupFutures()
{
	// Remove any futures that have completed
	m_futures.erase(std::remove_if(m_futures.begin(), m_futures.end(), [](std::future<void>& f) {
		if (f.valid() && f.wait_for(std::chrono::seconds(0)) == std::future_status::ready)
		{
			f.get(); // Ensure the task is properly cleaned up
			return true; // Remove this future
		}
		return false;
	}), m_futures.end());
}

void Logger::debug(const string& msg, ...)
{
	if (m_level == LOG_ERR || m_level == LOG_WARNING || m_level == LOG_INFO)
	{
		return;
	}
	va_list args;
	va_start(args, msg);
	string *fmt = format(msg, args);
	syslog(LOG_DEBUG, "DEBUG: %s", fmt->c_str());
	executeInterceptor(LogLevel::DEBUG, fmt->c_str());
	delete fmt;
	va_end(args);
}

void Logger::printLongString(const string& s)
{
	const int charsPerLine = 950;
	int len = s.size();
	const char *cstr = s.c_str();
	for(int i=0; i<(len+charsPerLine-1)/charsPerLine; i++)
		Logger::getLogger()->debug("%s:%d: cstr[%d]=%s", __FUNCTION__, __LINE__, i*charsPerLine, cstr+i*charsPerLine);
}

void Logger::info(const string& msg, ...)
{
	if (m_level == LOG_ERR || m_level == LOG_WARNING)
	{
		return;
	}
	va_list args;
	va_start(args, msg);
	string *fmt = format(msg, args);
#ifdef ADD_USEC_TS
	syslog(LOG_INFO, "[.%06ld] INFO: %s", getCurrTimeUsec(), fmt->c_str());
#else
	syslog(LOG_INFO, "INFO: %s", fmt->c_str());
#endif
	executeInterceptor(LogLevel::INFO, fmt->c_str());
	delete fmt;
	va_end(args);
}

void Logger::warn(const string& msg, ...)
{
	va_list args;
	va_start(args, msg);
	string *fmt = format(msg, args);
	syslog(LOG_WARNING, "WARNING: %s", fmt->c_str());
	executeInterceptor(LogLevel::WARNING, fmt->c_str());
	delete fmt;
	va_end(args);
}

void Logger::error(const string& msg, ...)
{
	va_list args;
	va_start(args, msg);
	string *fmt = format(msg, args);
#ifdef ADD_USEC_TS
		syslog(LOG_ERR, "[.%06ld] ERROR: %s", getCurrTimeUsec(), fmt->c_str());
#else
		syslog(LOG_ERR, "ERROR: %s", fmt->c_str());
#endif
	executeInterceptor(LogLevel::ERROR, fmt->c_str());
	delete fmt;
	va_end(args);
}

void Logger::fatal(const string& msg, ...)
{
	va_list args;
	va_start(args, msg);
	string *fmt = format(msg, args);
	syslog(LOG_CRIT, "FATAL: %s", fmt->c_str());
	executeInterceptor(LogLevel::FATAL, fmt->c_str());
	delete fmt;
	va_end(args);
}

string *Logger::format( const std::string& format, va_list args)
{
char	buf[1000];

	  vsnprintf(buf, sizeof(buf), format.c_str(), args);
	  return new string(buf);
}

