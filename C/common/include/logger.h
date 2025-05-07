#ifndef _LOGGER_H
#define _LOGGER_H
/*
 * Fledge storage service.
 *
 * Copyright (c) 2017-2018 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch, Massimiliano Pinto
 */

#include <string>
#include <functional>
#include <map>
#include <mutex>
#include <queue>
#include <thread>
#include <condition_variable>
#include <atomic>
#include <sys/socket.h>
#include <arpa/inet.h>
#define PRINT_FUNC	Logger::getLogger()->info("%s:%d", __FUNCTION__, __LINE__);

/**
 * Fledge Logger class used to log to syslog
 *
 * At startup this class should be constructed
 * using the standard constructor. To log a message
 * call debug, info, warn etc. using the instance
 * of the class.
 *
 * To obtain that singleton instance call the static
 * method getLogger.
 *
 * It is generally unsafe to delete the logger class
 * as it may be called asynchronouly from multiple
 * threads and single handlers. The destructor has
 * hence been made private to prevent the destruction
 * of the class.
 */
class Logger {
	public:
		enum class LogLevel
		{
			ERROR,
			WARNING,
			INFO,
			DEBUG,
			FATAL
		};

		Logger(const std::string& application);
		~Logger();
		static Logger *getLogger();
		void debug(const std::string& msg, ...);
		void printLongString(const std::string&, LogLevel = LogLevel::DEBUG);
		void info(const std::string& msg, ...);
		void warn(const std::string& msg, ...);
		void error(const std::string& msg, ...);
		void fatal(const std::string& msg, ...);
		void setMinLevel(const std::string& level);
		std::string& getMinLevel() { return levelString; }

		// LogInterceptor callback function signature
		typedef void (*LogInterceptor)(LogLevel, const std::string&, void*);

		// Register an interceptor
		bool registerInterceptor(LogLevel level, LogInterceptor callback, void* userData);

		// Unregister an interceptor
		bool unregisterInterceptor(LogLevel level, LogInterceptor callback);

	private:
		std::string 	*format(const std::string& msg, va_list ap);
		static Logger   *instance;
		std::string     levelString;
		int		m_level;

		struct InterceptorData {
			LogInterceptor callback;
			void* userData;
		};

		std::multimap<LogLevel, InterceptorData> m_interceptors;
		std::mutex m_interceptorMapMutex;

		struct LogTask {
			LogLevel level;
			std::string message;
			LogInterceptor callback;
			void* userData;
		};

		std::queue<LogTask>	m_taskQueue;
		std::mutex		m_queueMutex;
		std::condition_variable m_condition;
		std::atomic<bool>	m_runWorker;
		std::thread 		*m_workerThread;

		void log(int sysLogLvl, const char * lvlName, LogLevel appLogLvl, const std::string& msg, ...);
		void sendToUdpSink(const std::string& msg);
		void executeInterceptor(LogLevel level, const std::string& message);
		void workerThread();
		int m_UdpSockFD = -1;
		struct sockaddr_in m_UdpServerAddr;
		bool m_SyslogUdpEnabled = false;
};

#endif

