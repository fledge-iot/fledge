cmake_minimum_required(VERSION 2.6)

project(sqlitememory)

set(CMAKE_CXX_FLAGS "-std=c++11 -O3")

set(STORAGE_COMMON_LIB storage-common-lib)

# Path of compiled libsqlite3.a and .h files: /tmp/sqlite3-pkg/src
set(FLEDGE_SQLITE3_LIBS "/tmp/sqlite3-pkg/src" CACHE INTERNAL "")

## sqlitememory plugin
include_directories(../../../../C/thirdparty/rapidjson/include)
include_directories(../../../../C/common/include)
include_directories(../../../../C/services/common/include)
include_directories(../../../../C/plugins/storage/common/include)
include_directories(../../../../C/plugins/storage/sqlitelb/include)
include_directories(../../../../C/plugins/storage/sqlitelb/common/include)

# Check Sqlite3 required version
set(CMAKE_MODULE_PATH ${CMAKE_MODULE_PATH} "${CMAKE_CURRENT_SOURCE_DIR}")
find_package(sqlite3)

# Find source files
file(GLOB COMMON_SOURCES ../../../../C/plugins/storage/sqlitelb/common/*.cpp)
file(GLOB COMMON_SOURCES2 ../../../../C/common/logger.cpp ../../../../C/common/string_utils.cpp ../../../../C/common/config_category.cpp ../../../../C/common/json_utils.cpp)
file(GLOB SOURCES ../../../../C/plugins/storage/sqlitememory/*.cpp)

# Create shared library

link_directories(${PROJECT_BINARY_DIR}/../../lib)

add_library( ${PROJECT_NAME} SHARED ${SOURCES} ${COMMON_SOURCES} ${COMMON_SOURCES2} )

add_definitions(-DSQLITE_SPLIT_READINGS=1)
add_definitions(-DPLUGIN_LOG_NAME="SQLite 3 in_memory")

if(EXISTS ${FLEDGE_SQLITE3_LIBS})
	include_directories(${FLEDGE_SQLITE3_LIBS})
	target_link_libraries(${PROJECT_NAME} -L"${FLEDGE_SQLITE3_LIBS}/.libs" -lsqlite3)
else()
	
	target_link_libraries(${PROJECT_NAME} -lsqlite3)
endif()

target_link_libraries(${PROJECT_NAME} ${STORAGE_COMMON_LIB})
set_target_properties(${PROJECT_NAME} PROPERTIES SOVERSION 1)
