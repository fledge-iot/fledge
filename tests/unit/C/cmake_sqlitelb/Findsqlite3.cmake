# This CMake file locates the SQLite3 development libraries
#
# The following variables are set:
# SQLITE_FOUND - If the SQLite library was found
# SQLITE_LIBRARIES - Path to the static library
# SQLITE_INCLUDE_DIR - Path to SQLite headers
# SQLITE_VERSION - Library version

set(SQLITE_MIN_VERSION "3.11.0")
# Check wether path of compiled libsqlite3.a and .h files exists
if (EXISTS ${FLEDGE_SQLITE3_LIBS})
    find_path(SQLITE_INCLUDE_DIR sqlite3.h PATHS ${FLEDGE_SQLITE3_LIBS})
    find_library(SQLITE_LIBRARIES NAMES libsqlite3.a PATHS "${FLEDGE_SQLITE3_LIBS}/.libs")
else()
    find_path(SQLITE_INCLUDE_DIR sqlite3.h)
    find_library(SQLITE_LIBRARIES NAMES libsqlite3.so)
endif()

if (SQLITE_INCLUDE_DIR AND SQLITE_LIBRARIES)
  execute_process(COMMAND grep ".*#define.*SQLITE_VERSION " ${SQLITE_INCLUDE_DIR}/sqlite3.h
    COMMAND sed "s/.*\"\\(.*\\)\".*/\\1/"
    OUTPUT_VARIABLE SQLITE_VERSION
    OUTPUT_STRIP_TRAILING_WHITESPACE)
    if ("${SQLITE_VERSION}" VERSION_LESS "${SQLITE_MIN_VERSION}")
        message(FATAL_ERROR "SQLite3 version >= ${SQLITE_MIN_VERSION} required, found version ${SQLITE_VERSION}")
    else()
        message(STATUS "Found SQLite version ${SQLITE_VERSION}: ${SQLITE_LIBRARIES}")
        set(SQLITE_FOUND TRUE)
    endif()
else()
  message(FATAL_ERROR "Could not find SQLite")
endif()
