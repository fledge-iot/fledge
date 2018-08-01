cmake_minimum_required(VERSION 2.4.0)

project(usb4704)

set(BIODAQDIR $ENV{BIODAQDIR})
find_library(BIODAQLIB biodaq ${BIODAQDIR}/libs)
set(CMAKE_CXX_FLAGS_DEBUG "-O0 -ggdb")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11")
find_library(COMMO_LIB common-lib ../../..)

# Find source files
file(GLOB SOURCES *.cpp)
link_directories(${PROJECT_BINARY_DIR}/../../../lib)

# Include header files
include_directories(include ../../../services/common/include ../common/include ../../../common/include ../../../thirdparty/rapidjson/include ${BIODAQDIR}/inc)
link_directories(${PROJECT_BINARY_DIR}/../../../lib)

file(GLOB SOURCES "*.cpp")

# Create shared library
add_library(${PROJECT_NAME} SHARED ${SOURCES})
target_link_libraries(${PROJECT_NAME} ${BIODAQLIB})
target_link_libraries(${PROJECT_NAME} ${COMMON_LIB})

set_target_properties(${PROJECT_NAME} PROPERTIES SOVERSION 1)

# Install library
install(TARGETS ${PROJECT_NAME} DESTINATION foglamp/plugins/south/${PROJECT_NAME})
