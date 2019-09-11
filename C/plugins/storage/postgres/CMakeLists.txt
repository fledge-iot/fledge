cmake_minimum_required(VERSION 2.6.0)

project(postgres)

set(CMAKE_CXX_FLAGS_DEBUG "-O0 -ggdb")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11")
set(STORAGE_COMMON_LIB storage-common-lib)

# Handle Postgres on RedHat/CentOS
set(CMAKE_MODULE_PATH ${CMAKE_MODULE_PATH} "${CMAKE_CURRENT_SOURCE_DIR}")
include(CheckRhPg)

# Find source files
file(GLOB SOURCES *.cpp)

# Include header files
include_directories(include ../../../common/include ../../../services/common/include ../common/include)
include_directories(../../../thirdparty/rapidjson/include)
link_directories(${PROJECT_BINARY_DIR}/../../../lib)

if(${RH_POSTGRES_FOUND} EQUAL 1)

    include_directories(${RH_POSTGRES_INCLUDE})
    link_directories(${RH_POSTGRES_LIB64})
else()
    include_directories(/usr/include/postgresql)
endif()

# Create shared library
add_library(${PROJECT_NAME} SHARED ${SOURCES})
set_target_properties(${PROJECT_NAME} PROPERTIES SOVERSION 1)
target_link_libraries(${PROJECT_NAME} -lpq)
target_link_libraries(${PROJECT_NAME} ${STORAGE_COMMON_LIB})

# Install library
install(TARGETS ${PROJECT_NAME} DESTINATION fledge/plugins/storage//${PROJECT_NAME})

# Install init.sql
install(FILES ${CMAKE_SOURCE_DIR}/scripts/plugins/storage/${PROJECT_NAME}/init.sql DESTINATION fledge/plugins/storage//${PROJECT_NAME})
