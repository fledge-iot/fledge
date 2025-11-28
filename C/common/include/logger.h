#ifndef _LOGGER_H
#define _LOGGER_H
/*
 * Fledge Logger virtual base class
 *
 * Copyright (c) 2017-2025 Dianomic Systems
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
#define PRINT_FUNC Logger::getLogger()->info("%s:%d", __FUNCTION__, __LINE__);

class Logger
{
public:
	enum class LogLevel
	{
		ERROR,
		WARNING,
		INFO,
		DEBUG,
		FATAL
	};

	// LogInterceptor callback function signature
	typedef void (*LogInterceptor)(LogLevel, const std::string &, void *);

	virtual ~Logger() = 0;
	static Logger *getLogger();
	static Logger *getNewLogger(const std::string &application);
	virtual void debug(const std::string &msg, ...) = 0;
	virtual void printLongString(const std::string &, LogLevel = LogLevel::DEBUG) = 0;
	virtual void info(const std::string &msg, ...) = 0;
	virtual void warn(const std::string &msg, ...) = 0;
	virtual void error(const std::string &msg, ...) = 0;
	virtual void fatal(const std::string &msg, ...) = 0;
	virtual void setMinLevel(const std::string &level) = 0;
	virtual std::string &getMinLevel() = 0;

	// Register an interceptor
	virtual bool registerInterceptor(LogLevel level, LogInterceptor callback, void *userData) = 0;

	// Unregister an interceptor
	virtual bool unregisterInterceptor(LogLevel level, LogInterceptor callback) = 0;

protected:
	static Logger *instance;
	Logger() = default;
	Logger(const std::string &application);
};

#endif
