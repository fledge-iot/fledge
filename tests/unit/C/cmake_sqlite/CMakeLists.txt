cmake_minimum_required(VERSION 2.6)

project(sqlitememory)

set(CMAKE_CXX_FLAGS "-std=c++11 -O3")

set(STORAGE_COMMON_LIB storage-common-lib)

## sqlitememory plugin
include_directories(../../../../C/thirdparty/rapidjson/include)
include_directories(../../../../C/common/include)
include_directories(../../../../C/services/common/include)
include_directories(../../../../C/plugins/storage/common/include)
include_directories(../../../../C/plugins/storage/sqlite/include)
include_directories(../../../../C/plugins/storage/sqlite/common/include)

# Check Sqlite3 required version
set(CMAKE_MODULE_PATH ${CMAKE_MODULE_PATH} "${CMAKE_CURRENT_SOURCE_DIR}")
find_package(sqlite3)

# Find source files
file(GLOB COMMON_SOURCES ../../../../C/plugins/storage/sqlite/common/*.cpp)
file(GLOB SOURCES ../../../../C/plugins/storage/sqlitememory/*.cpp)

# Create shared library

link_directories(${PROJECT_BINARY_DIR}/../../lib)

add_library(${PROJECT_NAME} SHARED ${SOURCES} ${COMMON_SOURCES})

add_definitions(-DSQLITE_SPLIT_READINGS=1)
add_definitions(-DPLUGIN_LOG_NAME="SQLite 3 in_memory")

target_link_libraries(${PROJECT_NAME} -lsqlite3)
target_link_libraries(${PROJECT_NAME} ${STORAGE_COMMON_LIB})
set_target_properties(${PROJECT_NAME} PROPERTIES SOVERSION 1)
