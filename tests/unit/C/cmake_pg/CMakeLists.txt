cmake_minimum_required(VERSION 2.6)

project(postgres)

set(CMAKE_CXX_FLAGS "-std=c++11 -O3")

set(STORAGE_COMMON_LIB storage-common-lib)

# postgres plugin
include_directories(/usr/include/postgresql)
include_directories(../../../../C/thirdparty/rapidjson/include)
include_directories(../../../../C/common/include)
include_directories(../../../../C/services/common/include)
include_directories(../../../../C/plugins/storage/common/include)
include_directories(../../../../C/plugins/storage/postgres/include)

# Find source files
file(GLOB SOURCES ../../../../C/plugins/storage/postgres/*.cpp)

# Create shared library
link_directories(${PROJECT_BINARY_DIR}/../../lib)

add_library(${PROJECT_NAME} SHARED ${SOURCES})
target_link_libraries(${PROJECT_NAME} -lpq)
target_link_libraries(${PROJECT_NAME} ${STORAGE_COMMON_LIB})
set_target_properties(${PROJECT_NAME} PROPERTIES SOVERSION 1)
