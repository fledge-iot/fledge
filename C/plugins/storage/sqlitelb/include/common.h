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
#include <connection.h>

#define	STORAGE_PURGE_RETAIN_ANY 0x0001U
#define	STORAGE_PURGE_RETAIN_ALL 0x0002U
#define STORAGE_PURGE_SIZE	     0x0004U

#define  DB_CONFIGURATION "PRAGMA busy_timeout = 5000; PRAGMA cache_size = -4000; PRAGMA journal_mode = WAL; PRAGMA secure_delete = off; PRAGMA journal_size_limit = 4096000;"

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
