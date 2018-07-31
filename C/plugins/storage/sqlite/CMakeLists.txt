cmake_minimum_required(VERSION 2.4.0)

project(sqlite)

set(CMAKE_CXX_FLAGS_DEBUG "-O0 -ggdb")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11")
set(STORAGE_COMMON_LIB -lstorage-common-lib)

# Find source files
file(GLOB SOURCES *.cpp)

# Include header files
include_directories(include ../../../common/include ../../../services/common/include ../common/include)
include_directories(../../../thirdparty/rapidjson/include)
link_directories(${PROJECT_BINARY_DIR}/../../../lib)

# Create shared library
add_library(${PROJECT_NAME} SHARED ${SOURCES})
target_link_libraries(${PROJECT_NAME} ${STORAGE_COMMON_LIB})
set_target_properties(${PROJECT_NAME} PROPERTIES SOVERSION 1)

# Check Sqlite3 required version
set(CMAKE_MODULE_PATH ${CMAKE_MODULE_PATH} "${CMAKE_CURRENT_SOURCE_DIR}")
find_package(sqlite3)

# Link with SQLite3 library
target_link_libraries(${PROJECT_NAME} -lsqlite3)

# Install library
install(TARGETS ${PROJECT_NAME} DESTINATION foglamp/plugins/storage/${PROJECT_NAME})

# Install init.sql
install(FILES ${CMAKE_SOURCE_DIR}/scripts/plugins/storage/${PROJECT_NAME}/init.sql DESTINATION foglamp/plugins/storage/${PROJECT_NAME})
