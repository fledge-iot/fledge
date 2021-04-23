# Project configuration
project(RunTests)
cmake_minimum_required(VERSION 2.6)
set(CMAKE_CXX_FLAGS "-std=c++11 -O3")

# libraries
set(LIBCURL_LIB -lcurl)

# Fledge libraries
set(COMMON_LIB              common-lib)
set(SERVICE_COMMON_LIB      services-common-lib)
set(PLUGINS_COMMON_LIB      plugins-common-lib)
set(PLUGIN_SQLITEMEMORY     sqlitememory)
set(STORAGE_COMMON_LIB      storage-common-lib)

# Locate GTest
find_package(GTest REQUIRED)

# Include files
include_directories(${GTEST_INCLUDE_DIRS})
include_directories(../../../../../../C/common/include)
include_directories(../../../../../../C/services/common/include)
include_directories(../../../../../../C/plugins/storage/common/include)
include_directories(../../../../../../C/thirdparty/rapidjson/include)
include_directories(../../../../../../C/plugins/storage/sqlitelb/include)
include_directories(../../../../../../C/plugins/storage/sqlitelb/common/include)

# Source files
file(GLOB COMMON_SOURCES ../sqlitelb/common/*.cpp)
file(GLOB COMMON_SOURCES ../sqlitememory/*.cpp)
file(GLOB test_sources tests.cpp)

# Check for SQLite3 source tree in specific location
set(FLEDGE_SQLITE3_LIBS "/tmp/sqlite3-pkg/src" CACHE INTERNAL "")
if(EXISTS ${FLEDGE_SQLITE3_LIBS})
	message(STATUS "Using SLITE3 source files in ${FLEDGE_SQLITE3_LIBS}")
	include_directories(${FLEDGE_SQLITE3_LIBS})
endif()

# Exe creation
link_directories(
        ${PROJECT_BINARY_DIR}/../../../../lib
)

add_executable(${PROJECT_NAME} ${test_sources} ${COMMON_SOURCES})

target_link_libraries(${PROJECT_NAME} ${COMMON_LIB})
target_link_libraries(${PROJECT_NAME} ${SERVICE_COMMON_LIB})
target_link_libraries(${PROJECT_NAME} ${PLUGINS_COMMON_LIB})

target_link_libraries(${PROJECT_NAME} ${PLUGIN_SQLITEMEMORY})
target_link_libraries(${PROJECT_NAME} ${STORAGE_COMMON_LIB})
target_link_libraries(${PROJECT_NAME} ${LIBCURL_LIB})

target_link_libraries(${PROJECT_NAME} ${GTEST_LIBRARIES} pthread)
