cmake_minimum_required(VERSION 2.6)

project(sqlite)

set(CMAKE_CXX_FLAGS "-std=c++11 -O3")

set(STORAGE_COMMON_LIB storage-common-lib)

# Path of compiled libsqlite3.a and .h files: /tmp/sqlite3-pkg/src
set(FLEDGE_SQLITE3_LIBS "/tmp/sqlite3-pkg/src" CACHE INTERNAL "")

## sqlite plugin
include_directories(../../../../C/thirdparty/rapidjson/include)
include_directories(../../../../C/common/include)
include_directories(../../../../C/services/common/include)
include_directories(../../../../C/plugins/storage/common/include)
include_directories(../../../../C/plugins/storage/sqlite/include)
include_directories(../../../../C/plugins/storage/sqlite/common/include)
include_directories(../../../../C/plugins/storage/sqlite/schema/include)

# Check Sqlite3 required version
set(CMAKE_MODULE_PATH ${CMAKE_MODULE_PATH} "${CMAKE_CURRENT_SOURCE_DIR}")
find_package(sqlite3)

# Find source files
file(GLOB COMMON_SOURCES ../../../../C/plugins/storage/sqlite/common/*.cpp)
file(GLOB SOURCES ../../../../C/plugins/storage/sqlite/*.cpp ../../../../C/plugins/storage/sqlite/schema/*.cpp)

# Create shared library

link_directories(${PROJECT_BINARY_DIR}/../../lib)

add_library(${PROJECT_NAME} SHARED ${SOURCES} ${COMMON_SOURCES})

add_definitions(-DPLUGIN_LOG_NAME="SQLite 3")

if(EXISTS ${FLEDGE_SQLITE3_LIBS})
	include_directories(${FLEDGE_SQLITE3_LIBS})
	target_link_libraries(${PROJECT_NAME} -L"${FLEDGE_SQLITE3_LIBS}/.libs" -lsqlite3)
else()
	
	target_link_libraries(${PROJECT_NAME} -lsqlite3)
endif()

target_link_libraries(${PROJECT_NAME} ${STORAGE_COMMON_LIB})
set_target_properties(${PROJECT_NAME} PROPERTIES SOVERSION 1)
