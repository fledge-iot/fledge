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
#include <exception>
#include <stdexcept>

using namespace std;

// uncomment line below to get uSec level timestamps
// #define ADD_USEC_TS

inline long getCurrTimeUsec()
{
	struct timeval m_timestamp;
	gettimeofday(&m_timestamp, NULL);
	return m_timestamp.tv_usec;
}

/**
 * The singleton pointer
 */
Logger *Logger::instance = 0;

/**
 * Constructor for the Logger class.
 *
 * @param application	The application name
 */
Logger::Logger(const string& application) : m_runWorker(true), m_workerThread(NULL)
{
static char ident[80];

	if (instance)
	{
		instance->error("Attempt to create second singleton instance, original application name %s, current attempt made by %s", ident, application.c_str());
		throw runtime_error("Attempt to create secnd Logger instance");
	}
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
}

/**
 * Destructor for the logger class.
 */
Logger::~Logger()
{
	// Stop the getLogger() call returning a deleted instance
	if (instance == this)
		instance = NULL;
	else if (!instance)
		return;	// Already destroyed
	m_condition.notify_one();
	if (m_workerThread && m_workerThread->joinable())
	{
		m_runWorker = false;
		m_workerThread->join();
		delete m_workerThread;
		m_workerThread = NULL;
	}

	closelog();
}

/**
 * Return the singleton instance of the logger class.
 */
Logger *Logger::getLogger()
{
	if (!instance)
	{
		// Any service should have already created the logger
		// for the service. If not then create the deault logger
		// and clearly identify this. We should ideally avoid
		// the use of a default as this will not identify the
		// source of the log message.
		instance = new Logger("(default)");
	}

	return instance;
}

/**
 * Set the minimum level of logging to write to syslog.
 *
 * @param level	The minimum, inclusive, level of logging to write
 */
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

/**
 * Register a callback function to be called when
 * a log message is written that matches the secification
 * given.
 *
 * Note: The callback functions are called on a seperate thread.
 * This worker thread is only created when the first callback is
 * registered.
 *
 * @param level		The level that must be matched
 * @param callback	The funtion to be called
 * @param userData	User date to pass to the callback function
 * @return bool		Return true if the callback was registered
 */
bool Logger::registerInterceptor(LogLevel level, LogInterceptor callback, void* userData)
{
	// Do not register the interceptor if callback function is null
	if (callback == nullptr)
	{
		return false;
	}

	std::lock_guard<std::mutex> lock(m_interceptorMapMutex);
	if (m_workerThread == NULL)
	{
		m_workerThread = new std::thread(&Logger::workerThread, this);
	}
	auto it = m_interceptors.emplace(level, InterceptorData{callback, userData});
	if (it != m_interceptors.end())
	{
		return true;
	}
	return false;
}

/**
 * Remove the registration of a previosuly registered callback
 *
 * @param level		The matching log loevel for the callback
 * @param callback	The callback to unregister
 * @return bool		True if the callback was unregistered.
 */
bool Logger::unregisterInterceptor(LogLevel level, LogInterceptor callback)
{
	std::lock_guard<mutex> lock(m_interceptorMapMutex);
	auto range = m_interceptors.equal_range(level);
	for (auto it = range.first; it != range.second; ++it)
	{
		if (it->second.callback == callback)
		{
			m_interceptors.erase(it);
			return true;
		}
	}
	return false;
}

/**
 * Queue the execution of a callback when a log message is received
 * that matches a registered callback
 *
 * @param level		The log level
 * @param message	The log message
 */
void Logger::executeInterceptor(LogLevel level, const std::string& message)
{
	std::lock_guard<mutex> lock(m_interceptorMapMutex);
	auto range = m_interceptors.equal_range(level);
	for (auto it = range.first; it != range.second; ++it)
	{
		std::lock_guard<mutex> lock(m_queueMutex);
		m_taskQueue.push({level, message, it->second.callback, it->second.userData});
	}
	m_condition.notify_one();
}

/**
 * The worker thread that processes intercepted log messages and
 * calls the callback function to handle them
 */
void Logger::workerThread()
{
	while (m_runWorker)
	{
		std::unique_lock<mutex> lock(m_queueMutex);
		m_condition.wait(lock, [this] { return !m_taskQueue.empty() || !m_runWorker; });

		while (!m_taskQueue.empty())
		{
			if(!m_runWorker) //Exit immediately during shutdown
			{
				return;
			}

			LogTask task = m_taskQueue.front();
			m_taskQueue.pop();
			lock.unlock();

			if (task.callback)
			{
				task.callback(task.level, task.message, task.userData);
			}

			lock.lock();
		}
	}
}

/**
 * Log a message at the level debug
 *
 * @param msg		A printf format string
 * @param ...		The variable arguments required by the printf format
 */
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
	if (!m_interceptors.empty())
	{
		executeInterceptor(LogLevel::DEBUG, fmt->c_str());
	}
	delete fmt;
	va_end(args);
}

/**
 * Log a long string across multiple syslog entries
 *
 * @param s	The string to log
 * @param level	level to log the string at
 */
void Logger::printLongString(const string& s, LogLevel level)
{
	const int charsPerLine = 950;
	int len = s.size();
	const char *cstr = s.c_str();
	for (int i=0; i<(len+charsPerLine-1)/charsPerLine; i++)
	{
		switch (level)
		{
			case LogLevel::FATAL:
				this->fatal("%.*s%s",
						charsPerLine,
						cstr+i*charsPerLine,
						len - i > charsPerLine ? "..." : "");
				break;
			case LogLevel::ERROR:
				this->error("%.*s%s",
						charsPerLine,
						cstr+i*charsPerLine,
						len - i > charsPerLine ? "..." : "");
				break;
			case LogLevel::WARNING:
				this->warn("%.*s%s",
						charsPerLine,
						cstr+i*charsPerLine,
						len - i > charsPerLine ? "..." : "");
				break;
			case LogLevel::INFO:
				this->info("%.*s%s",
						charsPerLine,
						cstr+i*charsPerLine,
						len - i > charsPerLine ? "..." : "");
				break;
			case LogLevel::DEBUG:
			default:
				this->debug("%.*s%s",
						charsPerLine,
						cstr+i*charsPerLine,
						len - i > charsPerLine ? "..." : "");
				break;
		}
	}
}


/**
 * Log a message at the level info
 *
 * @param msg		A printf format string
 * @param ...		The variable arguments required by the printf format
 */
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
	if (!m_interceptors.empty())
	{
		executeInterceptor(LogLevel::INFO, fmt->c_str());
	}
	delete fmt;
	va_end(args);
}


/**
 * Log a message at the level warn
 *
 * @param msg		A printf format string
 * @param ...		The variable arguments required by the printf format
 */
void Logger::warn(const string& msg, ...)
{
	va_list args;
	va_start(args, msg);
	string *fmt = format(msg, args);
	syslog(LOG_WARNING, "WARNING: %s", fmt->c_str());
	if (!m_interceptors.empty())
	{
		executeInterceptor(LogLevel::WARNING, fmt->c_str());
	}
	delete fmt;
	va_end(args);
}


/**
 * Log a message at the level error
 *
 * @param msg		A printf format string
 * @param ...		The variable arguments required by the printf format
 */
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
	if (!m_interceptors.empty())
	{
		executeInterceptor(LogLevel::ERROR, fmt->c_str());
	}
	delete fmt;
	va_end(args);
}


/**
 * Log a message at the level fatal
 *
 * @param msg		A printf format string
 * @param ...		The variable arguments required by the printf format
 */
void Logger::fatal(const string& msg, ...)
{
	va_list args;
	va_start(args, msg);
	string *fmt = format(msg, args);
	syslog(LOG_CRIT, "FATAL: %s", fmt->c_str());
	if (!m_interceptors.empty())
	{
		executeInterceptor(LogLevel::FATAL, fmt->c_str());
	}
	delete fmt;
	va_end(args);
}

/**
 * Apply the formatting to the error message
 * 
 * @param format	The printf format string
 * @param args		The printf argument list
 * @return string	The formatted string
 */
string *Logger::format( const std::string& format, va_list args)
{
char	buf[1000];

	  vsnprintf(buf, sizeof(buf), format.c_str(), args);
	  return new string(buf);
}

