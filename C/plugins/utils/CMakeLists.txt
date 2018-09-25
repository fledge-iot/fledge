cmake_minimum_required(VERSION 2.4.0)

project(get_plugin_info)

set(CMAKE_CXX_FLAGS_DEBUG "-O0 -ggdb")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11")

# Include header files
include_directories(include ../../services/common/include)

# Create get_plugin_info utility
add_executable(${PROJECT_NAME} get_plugin_info.cpp)
target_link_libraries(${PROJECT_NAME} -ldl)

# Install library
install(TARGETS ${PROJECT_NAME} DESTINATION foglamp/extras/C)
