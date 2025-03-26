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
#include <unordered_map>
#include <memory>
#include <mutex>
#include <functional>
#include <vector>
#include <future> // For std::async

#define PRINT_FUNC	Logger::getLogger()->info("%s:%d", __FUNCTION__, __LINE__);

/**
 * Fledge Logger class used to log to syslog
 *
 * At startup this class should be constructed
 * using the standard constructor. To log a message
 * call debug, info, warn etc. using the instance
 * of the class. TO get that instance call the static
 * method getLogger.
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
		void printLongString(const std::string&);
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
		struct LogInterceptorNode
		{
			LogInterceptor callback;
			void* userData;
		};

		using InterceptorMap = std::unordered_multimap<LogLevel, LogInterceptorNode>;

		void executeInterceptor(LogLevel level, const std::string& message);
		std::string 	*format(const std::string& msg, va_list ap);
		static Logger   *instance;
		std::string     levelString;
		int		m_level;
		std::mutex m_interceptorMapMutex; // Mutex to protect the interceptor map
		std::shared_ptr<InterceptorMap> m_interceptors; // Shared pointer to interceptor map
		std::vector<std::future<void>> m_futures; // Futures for async tasks
		const  int m_futuresCountLimit = 10;
		void cleanupFutures(); // Clean up finished futures
};

#endif

