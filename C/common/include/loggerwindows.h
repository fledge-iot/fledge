#pragma once
#ifdef _WIN32
/*
 * Fledge Logger for Windows
 *
 * Copyright (c) 2025 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Ray Verhoeff
 */

 #include "logger.h"

#define PRINT_FUNC Logger::getLogger()->info("%s:%d", __FUNCTION__, __LINE__);

class LoggerWindows : public virtual Logger
{
public:
	LoggerWindows() = default;
	LoggerWindows(const std::string &application);
	~LoggerWindows();
	static LoggerWindows *getLogger();
	static Logger *getNewLogger(const std::string &application);
	void debug(const std::string &msg, ...) override;
	void printLongString(const std::string &, LogLevel = LogLevel::DEBUG) override;
	void info(const std::string &msg, ...) override;
	void warn(const std::string &msg, ...) override;
	void error(const std::string &msg, ...) override;
	void fatal(const std::string &msg, ...) override;
	void setMinLevel(const std::string &level) override;
	std::string &getMinLevel() override { return levelString; }

	// Register an interceptor
	bool registerInterceptor(LogLevel level, LogInterceptor callback, void *userData) override;

	// Unregister an interceptor
	bool unregisterInterceptor(LogLevel level, LogInterceptor callback) override;

private:
	HANDLE m_eventLogHandle;
	std::string *format(const std::string &msg, va_list ap);
	std::string levelString;
	WORD m_level;

	struct InterceptorData
	{
		LogInterceptor callback;
		void *userData;
	};

	std::multimap<LogLevel, InterceptorData> m_interceptors;
	std::mutex m_interceptorMapMutex;

	struct LogTask
	{
		LogLevel level;
		std::string message;
		LogInterceptor callback;
		void *userData;
	};

	std::queue<LogTask> m_taskQueue;
	std::mutex m_queueMutex;
	std::condition_variable m_condition;
	std::atomic<bool> m_runWorker;
	std::thread *m_workerThread;

	void log(const WORD sysLogLvl, const char *lvlName, LogLevel appLogLvl, const std::string &msg, va_list args);
	void sendToUdpSink(const std::string &msg);
	void executeInterceptor(LogLevel level, const std::string &message);
	void workerThread();
	int m_UdpSockFD = -1;
	struct sockaddr_in m_UdpServerAddr;
	bool m_SyslogUdpEnabled = false;
	std::string m_identifier;
	std::string m_hostname;
};

#endif
