cmake_minimum_required(VERSION 2.6.0)

project(sqlitememory)

set(CMAKE_CXX_FLAGS_DEBUG "-O0 -ggdb")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11")
set(STORAGE_COMMON_LIB storage-common-lib)

# Path of compiled libsqlite3.a and .h files: /tmp/foglamp-sqlite3-pkg/src
set(FOGLAMP_SQLITE3_LIBS "/tmp/foglamp-sqlite3-pkg/src" CACHE INTERNAL "")

# Find source files
# Add sqlite plugin common files
file(GLOB COMMON_SOURCES ../sqlite/common/*.cpp)
# Add sqlitememory files
file(GLOB SOURCES *.cpp)

# Include header files
include_directories(../../../common/include)
include_directories(../../../services/common/include)
include_directories(../common/include)
include_directories(../../../thirdparty/rapidjson/include)
# Add sqlite plugin header files
include_directories(../sqlite/include)
include_directories(../sqlite/common/include)

link_directories(${PROJECT_BINARY_DIR}/../../../lib)

# Create shared library
add_library(${PROJECT_NAME} SHARED ${SOURCES} ${COMMON_SOURCES})
set_target_properties(${PROJECT_NAME} PROPERTIES SOVERSION 1)
target_link_libraries(${PROJECT_NAME} ${STORAGE_COMMON_LIB})

# Check Sqlite3 required version
set(CMAKE_MODULE_PATH ${CMAKE_MODULE_PATH} "${CMAKE_CURRENT_SOURCE_DIR}")
find_package(sqlite3)

add_definitions(-DSQLITE_SPLIT_READINGS=1)
add_definitions(-DPLUGIN_LOG_NAME="SQLite 3 in_memory")

# Use static SQLite3 library
if(EXISTS ${FOGLAMP_SQLITE3_LIBS})
        include_directories(${FOGLAMP_SQLITE3_LIBS})
        target_link_libraries(${PROJECT_NAME} -L"${FOGLAMP_SQLITE3_LIBS}/.libs" -lsqlite3)
else()
	# Link with SQLite3 library
	target_link_libraries(${PROJECT_NAME} -lsqlite3)
endif()

# Install library
install(TARGETS ${PROJECT_NAME} DESTINATION foglamp/plugins/storage/${PROJECT_NAME})
