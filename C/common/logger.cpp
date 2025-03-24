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

	/* Prepend "Fledge " in all casaes other than Fledge itelf and Fledge Storage..
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
	m_threadsCreatedSinceLastCleanup = 0;
}


Logger::~Logger()
{
	closelog();
	// Stop the getLogger() call returning a deleted instance
	if (instance == this)
		instance = NULL;

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
	std::lock_guard<std::mutex> lock(m_mutex);
	auto it =  m_interceptors.emplace(level, LogInterceptorNode{callback, userData});
	if (it != m_interceptors.end())
	{
		return true;
	}

	return false;
}

bool Logger::unregisterInterceptor(LogLevel level, LogInterceptor callback)
{
	std::lock_guard<std::mutex> lock(m_mutex);
	auto range = m_interceptors.equal_range(level);
	for (auto it = range.first; it != range.second; ++it)
	{
		if (it->second.callback == callback)
		{
			m_interceptors.erase(it);
			return true; // Remove only one matching entry
		}
	}
	return false;
}

void Logger::executeInterceptor(LogLevel level, const std::string& message)
{
	// No interceptor is registered
	if (m_interceptors.empty())
	{
		return;
	}

	std::vector<LogInterceptorNode> interceptors;
	{
		std::lock_guard<std::mutex> lock(m_mutex);
		auto range = m_interceptors.equal_range(level);
		for (auto it = range.first; it != range.second; ++it)
		{
			interceptors.push_back(it->second);
		}
	}

	// Execute interceptors asynchronously using threads
	for (auto& interceptor : interceptors)
	{
		m_threads.emplace_back([interceptor, level, message]() {
			interceptor.callback(level, message, interceptor.userData);
		});
		m_threadsCreatedSinceLastCleanup++;
	}

	// Perform cleanup if the threshold is reached
	if (m_threadsCreatedSinceLastCleanup >= 10)
	{
		cleanupThreads();
		m_threadsCreatedSinceLastCleanup = 0;
	}
}

void Logger::cleanupThreads()
{
	std::lock_guard<std::mutex> lock(m_mutex);
	// Detach the threads
	m_threads.erase(std::remove_if(m_threads.begin(), m_threads.end(), [](std::thread& t) {
		if (t.joinable())
		{
			t.detach();
			return true; // Remove this thread
		}
		return false;
	}), m_threads.end());
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

