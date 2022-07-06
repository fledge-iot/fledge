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

add_definitions(-DMEMORY_READING_PLUGIN=1)

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

# Find python3.x dev/lib package
find_package(PkgConfig REQUIRED)
if(${CMAKE_VERSION} VERSION_LESS "3.12.0")
    pkg_check_modules(PYTHON REQUIRED python3)
else()
    find_package(Python3 COMPONENTS Interpreter Development)
endif()

# Add Python 3.x header files
if(${CMAKE_VERSION} VERSION_LESS "3.12.0")
    include_directories(${PYTHON_INCLUDE_DIRS})
else()
    include_directories(${Python3_INCLUDE_DIRS})
endif()

if(${CMAKE_VERSION} VERSION_LESS "3.12.0")
    link_directories(${PYTHON_LIBRARY_DIRS})
else()
    link_directories(${Python3_LIBRARY_DIRS})
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

# Add Python 3.x library
if(${CMAKE_VERSION} VERSION_LESS "3.12.0")
	target_link_libraries(${PROJECT_NAME} ${PYTHON_LIBRARIES})
else()
	target_link_libraries(${PROJECT_NAME} ${Python3_LIBRARIES})
endif()
