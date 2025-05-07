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
#include <sys/socket.h>
#include <exception>
#include <arpa/inet.h>

using namespace std;

// uncomment line below to get uSec level timestamps
// #define ADD_USEC_TS
const char * DEFALUT_LOG_IP = "127.0.0.1";
const int DEFAULT_LOG_PORT = 5140;

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

	// Check if SYSLOG_UDP_ENABLED is set via environment variable
	const char* udpEnabledEnv = std::getenv("SYSLOG_UDP_ENABLED");
	m_SyslogUdpEnabled = false;

	if (udpEnabledEnv != nullptr && std::string(udpEnabledEnv) == "true") 
	{
		m_SyslogUdpEnabled = true;
	}

	if(m_SyslogUdpEnabled)
	{
		// Check LOG_IP and LOG_PORT from environment variables with default values
		const char* logIpEnv = std::getenv("LOG_IP");
		const char* logPortEnv = std::getenv("LOG_PORT");

		std::string logIp = logIpEnv ? logIpEnv : DEFALUT_LOG_IP; // Default to 127.0.0.1
		int logPort = logPortEnv ? std::atoi(logPortEnv) : DEFAULT_LOG_PORT; // Default to port 5140
		// Initialize the UDP socket
		m_UdpSockFD = socket(AF_INET, SOCK_DGRAM, 0);
		if (m_UdpSockFD >= 0) 
		{
			memset(&m_UdpServerAddr, 0, sizeof(m_UdpServerAddr));
			m_UdpServerAddr.sin_family = AF_INET;
			m_UdpServerAddr.sin_port = htons(logPort); // Use the port from LOG_PORT or default
			if (inet_pton(AF_INET, logIp.c_str(), &m_UdpServerAddr.sin_addr) <= 0)
			{
				throw std::runtime_error("Invalid LOG_IP address");
			}
		} 
		else 
		{
			throw std::runtime_error("Failed to create UDP socket");
		}
	}
	else
	{
		openlog(ident, LOG_PID|LOG_CONS, LOG_USER);
	}

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

	if(!m_SyslogUdpEnabled)
	{
		closelog();
	}
	else
	{
		if (m_UdpSockFD >= 0) 
		{
			close(m_UdpSockFD);
			m_UdpSockFD = -1;
		}
	}
}

/**
 * Send a message to the UDP sink if enabled
 *
 * @param msg		The message to send
 */
void Logger::sendToUdpSink(const std::string& msg) 
{
	if (m_UdpSockFD >= 0) 
	{
		sendto(m_UdpSockFD, msg.c_str(), msg.size(), 0, (struct sockaddr*)&m_UdpServerAddr, sizeof(m_UdpServerAddr));
	}
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
	va_list args;
	va_start(args, msg);

	// Use the unified log function with the "DEBUG" level
	log(LOG_DEBUG, "DEBUG", LogLevel::DEBUG, msg, args);

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
void Logger::info(const std::string& msg, ...)
{
	va_list args;
	va_start(args, msg);

	// Use the unified log function with the "INFO" level
	log(LOG_INFO, "INFO", LogLevel::INFO, msg, args);

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

	// Use the unified log function with the "WARNING" level
	log(LOG_WARNING, "WARNING", LogLevel::WARNING, msg, args);

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

	// Use the unified log function with the "ERROR" level
	log(LOG_ERR, "ERROR", LogLevel::ERROR, msg, args);

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

	// Use the unified log function with the "FATAL" level
	log(LOG_CRIT, "FATAL", LogLevel::FATAL, msg, args);

	va_end(args);
}

/**
 * Log a message at the specified level
 *
 * @param sysLogLvl	The syslog level to use
 * @param lvlName		The name of the log level
 * @param appLogLvl	The application log level
 * @param msg		A printf format string
 * @param ...		The variable arguments required by the printf format
 */
void Logger::log(int sysLogLvl, const char * lvlName, LogLevel appLogLvl, const std::string& msg, ...)
{
	// Check if the current log level allows messages
	if (m_level < sysLogLvl) 
	{
		return;
	}

	constexpr size_t MAX_BUFFER_SIZE = 1024; // Maximum allowed log size
	char buffer[MAX_BUFFER_SIZE]; // Stack-allocated buffer for formatting

	va_list args;
	va_start(args, msg);

	int copied = 0;

#ifdef ADD_USEC_TS
	copied = snprintf(buffer, sizeof(buffer), "[.%06ld] %s: ", getCurrTimeUsec(), lvlName);
#else
	copied = snprintf(buffer, sizeof(buffer), "%s: ", lvlName);
#endif

	// Format the log message using vsnprintf
	vsnprintf(buffer + copied, sizeof(buffer) - copied, msg.c_str(), args);
	va_end(args); // Ensure `va_list` is cleaned up immediately after usage

	if(m_SyslogUdpEnabled)
	{
		// Send the message to the UDP sink
		sendToUdpSink(buffer);
	}
	else
	{
		syslog(sysLogLvl, buffer);
	}

	// Execute interceptors if any are present
	if (!m_interceptors.empty())
	{
		executeInterceptor(appLogLvl, buffer);
	}
}
