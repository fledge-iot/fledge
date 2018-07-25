cmake_minimum_required(VERSION 2.4.0)

project(plugins-common-lib)

set(CMAKE_CXX_FLAGS_DEBUG "-O0 -ggdb")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11")

# Find source files
file(GLOB SOURCES *.cpp)

# Include header files
include_directories(include ../../common/include ../../thirdparty/Simple-Web-Server)

set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${PROJECT_BINARY_DIR}/../../lib)

# Create shared library
add_library(${PROJECT_NAME} SHARED ${SOURCES})

set_target_properties(${PROJECT_NAME} PROPERTIES SOVERSION 1)

# Install library
install(TARGETS ${PROJECT_NAME} DESTINATION foglamp/lib)
