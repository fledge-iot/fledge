cmake_minimum_required(VERSION 2.4.0)

project(postgres)

set(CMAKE_CXX_FLAGS_DEBUG "-O0 -ggdb")

# Find source files
file(GLOB SOURCES *.cpp)

# Include header files
include_directories(include ../../../common/include ../common/include)
include_directories(../../../../thirdparty/rapidjson/include /usr/include/postgresql)

file(GLOB SOURCES "*.cpp" ../common/*.cpp)

# Create shared library
add_library(${PROJECT_NAME} SHARED ${SOURCES})
set_target_properties(${PROJECT_NAME} PROPERTIES SOVERSION 1)
target_link_libraries(${PROJECT_NAME} -lpq)

# Install library
install(TARGETS ${PROJECT_NAME} DESTINATION lib/${PROJECT_NAME})
