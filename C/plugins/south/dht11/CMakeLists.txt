cmake_minimum_required(VERSION 2.4.0)

project(dht11)

set(CMAKE_CXX_FLAGS_DEBUG "-O0 -ggdb")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11")
set(WIRINGPILIBS -lwiringPi -lwiringPiDev)

# Find source files
file(GLOB SOURCES *.cpp)

# Include header files
include_directories(include ../../../services/common/include ../common/include ../../../common/include ../../../thirdparty/rapidjson/include /usr/local/include/)

file(GLOB SOURCES "*.cpp" ../common/*.cpp)
#file(GLOB SOURCES plugin.cpp dht11.cpp ../common/*.cpp)
#file(GLOB TEST_SOURCES test.cpp dht11_basic.cpp ../common/*.cpp)

#add_executable(test ${TEST_SOURCES})
#target_link_libraries(test ${WIRINGPILIBS})

# Create shared library
add_library(${PROJECT_NAME} SHARED ${SOURCES})
target_link_libraries(${PROJECT_NAME} ${WIRINGPILIBS})

set_target_properties(${PROJECT_NAME} PROPERTIES SOVERSION 1)

# Install library
install(TARGETS ${PROJECT_NAME} DESTINATION foglamp/plugins/south/${PROJECT_NAME})
