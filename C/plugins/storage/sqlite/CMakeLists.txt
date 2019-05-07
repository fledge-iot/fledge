cmake_minimum_required(VERSION 2.6.0)

project(sqlite)

set(CMAKE_CXX_FLAGS_DEBUG "-O0 -ggdb")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11")
set(STORAGE_COMMON_LIB storage-common-lib)

# Find source files
file(GLOB SOURCES ./common/*.cpp *.cpp)

# Include header files
include_directories(./include)
include_directories(./common/include)
include_directories(../../../common/include)
include_directories(../../../services/common/include)
include_directories(../common/include)
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
execute_process(COMMAND bash "-c" "${CMAKE_CURRENT_SOURCE_DIR}/common/is_RHEL.sh" RESULT_VARIABLE ret)
if(ret EQUAL "0")
    message(" Red Hat or CentOS system ")
    target_link_libraries(${PROJECT_NAME} /usr/local/lib/libsqlite3.so)
else()
    message(" Not a Red Hat or CentOS system ")
    target_link_libraries(${PROJECT_NAME} -lsqlite3)
endif()

# Install library
install(TARGETS ${PROJECT_NAME} DESTINATION foglamp/plugins/storage/${PROJECT_NAME})

# Install init.sql
install(FILES ${CMAKE_SOURCE_DIR}/scripts/plugins/storage/${PROJECT_NAME}/init.sql DESTINATION foglamp/plugins/storage/${PROJECT_NAME})
