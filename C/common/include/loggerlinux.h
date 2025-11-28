#ifndef _LOGGERLINUX_H
#define _LOGGERLINUX_H
#ifdef __linux__
/*
 * Fledge Logger for Linux syslog
 *
 * Copyright (c) 2017-2025 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch, Massimiliano Pinto
 */

#include "logger.h"
#define PRINT_FUNC	Logger::getLogger()->info("%s:%d", __FUNCTION__, __LINE__);

/**
 * Fledge LoggerLinux class used to log to syslog
 * This is a subclass of virtual base class Logger
 *
 * At startup this class should be constructed
 * using the standard constructor. To log a message
 * call debug, info, warn etc. using the instance
 * of the class.
 *
 * To obtain that singleton instance call the static
 * method getLogger.
 *
 */
class LoggerLinux : public virtual Logger {
	public:
		LoggerLinux() = default;
		LoggerLinux(const std::string& application);
		~LoggerLinux();
		static LoggerLinux *getLogger();
		static Logger *getNewLogger(const std::string &application);
		void debug(const std::string& msg, ...) override;
		void printLongString(const std::string&, LogLevel = LogLevel::DEBUG) override;
		void info(const std::string& msg, ...) override;
		void warn(const std::string& msg, ...) override;
		void error(const std::string& msg, ...) override;
		void fatal(const std::string& msg, ...) override;
		void setMinLevel(const std::string& level) override;
		std::string& getMinLevel() override { return levelString; }

		// Register an interceptor
		bool registerInterceptor(LogLevel level, LogInterceptor callback, void* userData) override;

		// Unregister an interceptor
		bool unregisterInterceptor(LogLevel level, LogInterceptor callback) override;

	private:
		std::string 	*format(const std::string& msg, va_list ap);
		friend class Logger;
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

		void log(int sysLogLvl, const char * lvlName, LogLevel appLogLvl, const std::string& msg, va_list args);
		void sendToUdpSink(const std::string& msg);
		void executeInterceptor(LogLevel level, const std::string& message);
		void workerThread();
		int m_UdpSockFD = -1;
		struct sockaddr_in m_UdpServerAddr;
		bool m_SyslogUdpEnabled = false;
		std::string m_identifier;
		std::string m_hostname;
};

#endif
#endif
