cmake_minimum_required(VERSION 2.6)

project(postgres)

set(CMAKE_CXX_FLAGS "-std=c++11 -O3")

set(STORAGE_COMMON_LIB storage-common-lib)

# Handle Postgres on RedHat/CentOS
set(CMAKE_MODULE_PATH ${CMAKE_MODULE_PATH} "${CMAKE_CURRENT_SOURCE_DIR}")
include(CheckRhPg)

# postgres plugin
include_directories(../../../../C/thirdparty/rapidjson/include)
include_directories(../../../../C/common/include)
include_directories(../../../../C/services/common/include)
include_directories(../../../../C/plugins/storage/common/include)
include_directories(../../../../C/plugins/storage/postgres/include)

# Handle Postgres on RedHat/CentOS
if(${RH_POSTGRES_FOUND} EQUAL 1)

    include_directories(/opt/rh/rh-postgresql96/root/usr/include)
    link_directories(/opt/rh/rh-postgresql96/root/usr/lib64)
else()
    include_directories(/usr/include/postgresql)
endif()

# Find source files
file(GLOB SOURCES ../../../../C/plugins/storage/postgres/*.cpp)

# Create shared library
link_directories(${PROJECT_BINARY_DIR}/../../lib)

add_library(${PROJECT_NAME} SHARED ${SOURCES})
target_link_libraries(${PROJECT_NAME} -lpq)
target_link_libraries(${PROJECT_NAME} ${STORAGE_COMMON_LIB})
set_target_properties(${PROJECT_NAME} PROPERTIES SOVERSION 1)
