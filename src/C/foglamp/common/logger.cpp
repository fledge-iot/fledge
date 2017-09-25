#include <logger.h>
#include <stdio.h>
#include <unistd.h>
#include <syslog.h>
#include <stdarg.h>
#include <memory>

using namespace std;

Logger *Logger::instance = 0;

Logger::Logger(const string& application)
{
  openlog(application.c_str(), LOG_PID|LOG_CONS, LOG_USER);
  instance = this;
}

Logger::~Logger()
{
  closelog();
}

Logger *Logger::getLogger()
{
  return instance;
}

void Logger::debug(const string& msg, ...)
{
  va_list args;
  va_start(args, msg);
  string fmt = format(msg, args);
  syslog(LOG_DEBUG, "%s", fmt.c_str());
  va_end(args);
}

void Logger::info(const string& msg, ...)
{
  va_list args;
  va_start(args, msg);
  string fmt = format(msg, args);
  syslog(LOG_INFO, "%s", fmt.c_str());
  va_end(args);
}

void Logger::warn(const string& msg, ...)
{
  va_list args;
  va_start(args, msg);
  string fmt = format(msg, args);
  syslog(LOG_WARNING, "%s", fmt.c_str());
  va_end(args);
}

void Logger::error(const string& msg, ...)
{
  va_list args;
  va_start(args, msg);
  string fmt = format(msg, args);
  syslog(LOG_ERR, "%s", fmt.c_str());
  va_end(args);
}

void Logger::fatal(const string& msg, ...)
{
  va_list args;
  va_start(args, msg);
  string fmt = format(msg, args);
  syslog(LOG_CRIT, "%s", fmt.c_str());
  va_end(args);
}

string Logger::format( const std::string& format, va_list args)
{
    size_t size = (size_t)vsnprintf( nullptr, 0, format.c_str(), args) + 1; // Extra space for '\0'
    unique_ptr<char[]> buf( new char[ size ] ); 
    vsnprintf( buf.get(), size, format.c_str(), args);
    return string( buf.get(), buf.get() + size - 1 ); // We don't want the '\0' inside
}
