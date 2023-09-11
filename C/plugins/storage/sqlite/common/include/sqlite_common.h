#ifndef _COMMON_CONNECTION_H
#define _COMMON_CONNECTION_H

#include <sql_buffer.h>
#include <iostream>
#include <sqlite3.h>
#include "rapidjson/document.h"
#include "rapidjson/writer.h"
#include "rapidjson/stringbuffer.h"
#include "rapidjson/error/error.h"
#include "rapidjson/error/en.h"
#include <string>
#include <map>
#include <stdarg.h>
#include <stdlib.h>
#include <sstream>
#include <logger.h>
#include <time.h>
#include <unistd.h>
#include <chrono>
#include <thread>
#include <atomic>
#include <condition_variable>
#include <sys/time.h>

#define _DB_NAME                  "/fledge.db"
#define READINGS_DB_NAME_BASE     "readings"

#define  DB_CONFIGURATION "PRAGMA busy_timeout = 5000; PRAGMA cache_size = -4000; PRAGMA journal_mode = WAL; PRAGMA secure_delete = off; PRAGMA journal_size_limit = 4096000;"

#define LEN_BUFFER_DATE 100
#define F_TIMEH24_S             "%H:%M:%S"
#define F_DATEH24_S             "%Y-%m-%d %H:%M:%S"
#define F_DATEH24_M             "%Y-%m-%d %H:%M"
#define F_DATEH24_H             "%Y-%m-%d %H"
// This is the default datetime format in Fledge: 2018-05-03 18:15:00.622
#define F_DATEH24_MS            "%Y-%m-%d %H:%M:%f"
// Format up to seconds
#define F_DATEH24_SEC           "%Y-%m-%d %H:%M:%S"
#define SQLITE3_NOW             "strftime('%Y-%m-%d %H:%M:%f', 'now', 'localtime')"
// The default precision is milliseconds, it adds microseconds and timezone
#define SQLITE3_NOW_READING     "strftime('%Y-%m-%d %H:%M:%f000+00:00', 'now')"
#define SQLITE3_FLEDGE_DATETIME_TYPE "DATETIME"

#define	STORAGE_PURGE_RETAIN_ANY 0x0001U
#define	STORAGE_PURGE_RETAIN_ALL 0x0002U
#define STORAGE_PURGE_SIZE	 0x0004U

static std::map<std::string, std::string> sqliteDateFormat = {
                                                {"HH24:MI:SS",
                                                        F_TIMEH24_S},
                                                {"YYYY-MM-DD HH24:MI:SS.MS",
                                                        F_DATEH24_MS},
                                                {"YYYY-MM-DD HH24:MI:SS",
                                                        F_DATEH24_S},
                                                {"YYYY-MM-DD HH24:MI",
                                                        F_DATEH24_M},
                                                {"YYYY-MM-DD HH24",
                                                        F_DATEH24_H},
                                                {"", ""}
                                        };
#endif
