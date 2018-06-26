cmake_minimum_required(VERSION 2.4.0)

project(omf)

set(CMAKE_CXX_FLAGS_DEBUG "-O0 -ggdb")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11")

# Find source files
file(GLOB SOURCES *.cpp)
file(GLOB plugin_common_src "../../../plugins/common/*.cpp")

# Include header files
include_directories(include ../../../services/common/include ../../../thirdparty/Simple-Web-Server ../../../thirdparty/rapidjson/include ../../../common/include ../../../plugins/common/include)

# Create shared library
add_library(${PROJECT_NAME} SHARED ${SOURCES} ${plugin_common_src})
set_target_properties(${PROJECT_NAME} PROPERTIES SOVERSION 1)

# Install library
install(TARGETS ${PROJECT_NAME} DESTINATION foglamp/plugins/north/${PROJECT_NAME})
