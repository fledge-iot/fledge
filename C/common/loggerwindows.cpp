#ifdef _WIN32
/*
 * Fledge Logger for Windows
 * This implementation uses the classic Event Logging API
 *
 * Copyright (c) 2025 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Ray Verhoeff
 */

#include <winsock.h>
#include <windows.h>
#ifdef UNICODE
#undef UNICODE
#endif
#define BOOST_ASIO_DISABLE_THREADS 0
#undef ERROR
#include <unistd.h>
#include <sys/time.h>
#include <stdexcept>
#include <algorithm>
#include "loggerwindows.h"

using namespace std;

// uncomment line below to get uSec level timestamps
// #define ADD_USEC_TS
const char * DEFALUT_LOG_IP = "127.0.0.1";
const int DEFAULT_LOG_PORT = 5140;

/**
 * Translates Logger::LogLevel to Windows Event Log codes
 *
 * @param logLevel	Level from Logger::LogLevel enum
 * @return			Windows Event Log code
 */
static WORD LogLevelToEventLogLevel(const Logger::LogLevel logLevel)
{
	switch (logLevel)
	{
	case Logger::LogLevel::WARNING:
		return EVENTLOG_WARNING_TYPE;
	case Logger::LogLevel::INFO:
	case Logger::LogLevel::DEBUG:
		return EVENTLOG_INFORMATION_TYPE;
	case Logger::LogLevel::ERROR:
	case Logger::LogLevel::FATAL:
		return EVENTLOG_ERROR_TYPE;
	default:
		return EVENTLOG_SUCCESS;
	}
}

inline long getCurrTimeUsec()
{
	struct timeval m_timestamp;
	gettimeofday(&m_timestamp, NULL);
	return m_timestamp.tv_usec;
}

/**
 * Constructor for the LoggerWindows class.
 *
 * @param application	The application name
 */
LoggerWindows::LoggerWindows(const string& application)
{
	m_runWorker = true;
	m_workerThread = NULL;
	static char ident[80];

	if (instance)
	{
		instance->error("Attempt to create second singleton instance, original application name %s, current attempt made by %s", ident, application.c_str());
		throw runtime_error("Attempt to create second Logger instance");
	}
	/* Prepend "Fledge " in all cases other than Fledge itself and Fledge Storage.
	 */
	if (application.compare("FogLAMP") != 0 && application.compare("FogLAMP Storage") != 0)
	{
		snprintf(ident, sizeof(ident), "FogLAMP %s", application.c_str());
	}
	else
	{
		strncpy(ident, application.c_str(), sizeof(ident));
	}

    m_eventLogHandle = RegisterEventSource(NULL, "FogLAMP");
    if (m_eventLogHandle == NULL)
	{
		std::string exceptionMessage = "Failed to register event source " + application + " Error: " + std::to_string(GetLastError());
		throw std::runtime_error(exceptionMessage.c_str());
    }

	instance = this;
	m_level = EVENTLOG_WARNING_TYPE;
	m_identifier = ident;
}

/**
 * Destructor for the LoggerWindows class.
 */
LoggerWindows::~LoggerWindows()
{
	// Stop the getLogger() call returning a deleted instance
	if (instance == this)
		instance = NULL;
	else if (!instance)
		return;	// Already destroyed
	m_runWorker = false;
	m_condition.notify_one();
	if (m_workerThread && m_workerThread->joinable())
	{
		m_workerThread->join();
		delete m_workerThread;
		m_workerThread = NULL;
	}
	DeregisterEventSource(m_eventLogHandle);
}

/**
 * Send a message to the UDP sink if enabled
 *
 * @param msg		The message to send
 */
void LoggerWindows::sendToUdpSink(const std::string& msg) 
{
	if (m_UdpSockFD >= 0) 
	{
		sendto(m_UdpSockFD, msg.c_str(), msg.size(), 0, (struct sockaddr*)&m_UdpServerAddr, sizeof(m_UdpServerAddr));
	}
}

/**
 * Return the singleton instance of the LoggerWindows class.
 */
Logger *Logger::getLogger()
{
	if (!instance)
	{
		// Any service should have already created the LoggerWindows
		// for the service. If not then create the default LoggerWindows
		// and clearly identify this. We should ideally avoid
		// the use of a default as this will not identify the
		// source of the log message.
		instance = (Logger *)new LoggerWindows("(default)");
	}

	return instance;
}

Logger *Logger::getNewLogger(const std::string &application)
{
	return (Logger *)new LoggerWindows(application);
}

/**
 * Set the minimum level of logging to write to syslog.
 *
 * @param level	The minimum, inclusive, level of logging to write
 */
void LoggerWindows::setMinLevel(const string& level)
{
	if (level.compare("info") == 0)
	{
		levelString = level;
		m_level = EVENTLOG_INFORMATION_TYPE;
	} else if (level.compare("warning") == 0)
	{
		levelString = level;
		m_level = EVENTLOG_WARNING_TYPE;
	} else if (level.compare("debug") == 0)
	{
		levelString = level;
		m_level = EVENTLOG_INFORMATION_TYPE;		// Event Logger does not have a separate code for Debug
	} else if (level.compare("error") == 0)
	{
		levelString = level;
		m_level = EVENTLOG_ERROR_TYPE;				// Event Logger does not have a separate code for Fatal
	} else
	{
		error("Request to set unsupported log level %s", level.c_str());
	}
}

/**
 * Register a callback function to be called when
 * a log message is written that matches the specification
 * given.
 *
 * Note: The callback functions are called on a separate thread.
 * This worker thread is only created when the first callback is
 * registered.
 *
 * @param level		The level that must be matched
 * @param callback	The funtion to be called
 * @param userData	User date to pass to the callback function
 * @return bool		Return true if the callback was registered
 */
bool LoggerWindows::registerInterceptor(LogLevel level, LogInterceptor callback, void* userData)
{
	// Do not register the interceptor if callback function is null
	if (callback == nullptr)
	{
		return false;
	}

	std::lock_guard<std::mutex> lock(m_interceptorMapMutex);
	if (m_workerThread == NULL)
	{
		m_workerThread = new std::thread(&LoggerWindows::workerThread, this);
	}
	auto it = m_interceptors.emplace(level, InterceptorData{callback, userData});
	if (it != m_interceptors.end())
	{
		return true;
	}
	return false;
}

/**
 * Remove the registration of a previously registered callback
 *
 * @param level		The matching log level for the callback
 * @param callback	The callback to unregister
 * @return bool		True if the callback was unregistered.
 */
bool LoggerWindows::unregisterInterceptor(LogLevel level, LogInterceptor callback)
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
void LoggerWindows::executeInterceptor(LogLevel level, const std::string& message)
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
void LoggerWindows::workerThread()
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
void LoggerWindows::debug(const string& msg, ...)
{
	va_list args;
	va_start(args, msg);

	// Use the unified log function with the "DEBUG" level
	log(EVENTLOG_INFORMATION_TYPE, "DEBUG", LogLevel::DEBUG, msg, args);

	va_end(args);
}

/**
 * Log a long string across multiple syslog entries
 *
 * @param s	The string to log
 * @param level	level to log the string at
 */
void LoggerWindows::printLongString(const string& s, LogLevel level)
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
void LoggerWindows::info(const std::string& msg, ...)
{
	va_list args;
	va_start(args, msg);

	// Use the unified log function with the "INFO" level
	log(EVENTLOG_INFORMATION_TYPE, "INFO", LogLevel::INFO, msg, args);

	va_end(args);
}

/**
 * Log a message at the level warn
 *
 * @param msg		A printf format string
 * @param ...		The variable arguments required by the printf format
 */
void LoggerWindows::warn(const string& msg, ...)
{
	va_list args;
	va_start(args, msg);

	// Use the unified log function with the "WARNING" level
	log(EVENTLOG_WARNING_TYPE, "WARNING", LogLevel::WARNING, msg, args);

	va_end(args);
}

/**
 * Log a message at the level error
 *
 * @param msg		A printf format string
 * @param ...		The variable arguments required by the printf format
 */
void LoggerWindows::error(const string& msg, ...)
{
	va_list args;
	va_start(args, msg);

	// Use the unified log function with the "ERROR" level
	log(EVENTLOG_ERROR_TYPE, "ERROR", LogLevel::ERROR, msg, args);

	va_end(args);
}


/**
 * Log a message at the level fatal
 *
 * @param msg		A printf format string
 * @param ...		The variable arguments required by the printf format
 */
void LoggerWindows::fatal(const string& msg, ...)
{
	va_list args;
	va_start(args, msg);

	// Use the unified log function with the "FATAL" level
	log(EVENTLOG_ERROR_TYPE, "FATAL", LogLevel::FATAL, msg, args);

	va_end(args);
}

/**
 * Log a message at the specified level
 *
 * @param sysLogLvl	The Windows Event Logging level requested
 * @param lvlName		The name of the log level
 * @param appLogLvl	Logger::LogLevel requested
 * @param msg		A printf format string
 * @param ...		The variable arguments required by the printf format
 */
void LoggerWindows::log(const WORD sysLogLvl, const char *lvlName, LogLevel appLogLvl, const std::string &msg, va_list args)
{
	// Check if the current log level allows messages
	if (m_level < sysLogLvl)
	{
		return;
	}

	constexpr size_t MAX_BUFFER_SIZE = 1024; // Maximum allowed log size
	char buffer[MAX_BUFFER_SIZE];			 // Stack-allocated buffer for formatting

	int copied = 0;

#ifdef ADD_USEC_TS
	copied += snprintf(buffer + copied, sizeof(buffer) - copied, "[.%06ld] %s: ", getCurrTimeUsec(), lvlName);
#else
	copied += snprintf(buffer + copied, sizeof(buffer) - copied, "%s: ", lvlName);
#endif

	// Format the log message using vsnprintf
	vsnprintf(buffer + copied, sizeof(buffer) - copied, msg.c_str(), args);

	// TODO: Upgrade to Windows ETW to write messages to the Application and Services Logs.
	// The older Windows Event Log does not have a Debug target.
	// Workaround is to give Debug messages a different Event Id.
	DWORD eventIdentifier = 0x1000;
	if (strncmp(lvlName, "DEBUG", 5))
	{
		eventIdentifier = 0x2000;
	}

	LPCSTR pBuf = (LPCSTR)buffer;

	if (!ReportEvent(
			m_eventLogHandle,					// Event log handle
			LogLevelToEventLogLevel(appLogLvl), // Event type (e.g., Information, Warning, Error)
			0,									// Event category
			eventIdentifier,					// Event identifier
			NULL,								// User security identifier (optional)
			1,									// Number of strings to merge
			0,									// Size of raw data (optional)
			&pBuf,								// Array of strings to merge
			NULL								// Raw data (optional)
			))
	{
		std::string exceptionMessage = "ReportEvent failed. Error: " + std::to_string(GetLastError());
		throw runtime_error(exceptionMessage.c_str());
	}

	// Execute interceptors if any are present
	if (!m_interceptors.empty())
	{
		executeInterceptor(appLogLvl, buffer);
	}
}
#endif