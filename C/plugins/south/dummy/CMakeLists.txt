cmake_minimum_required(VERSION 2.4.0)

project(dummy)

set(CMAKE_CXX_FLAGS_DEBUG "-O0 -ggdb")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11")

# Find source files
file(GLOB SOURCES *.cpp)

# Include header files
include_directories(include ../../../services/common/include ../common/include ../../../common/include)

file(GLOB SOURCES "*.cpp" ../common/*.cpp)

# Create shared library
add_library(${PROJECT_NAME} SHARED ${SOURCES})
set_target_properties(${PROJECT_NAME} PROPERTIES SOVERSION 1)

# Install library
install(TARGETS ${PROJECT_NAME} DESTINATION foglamp/plugins/south/${PROJECT_NAME})
