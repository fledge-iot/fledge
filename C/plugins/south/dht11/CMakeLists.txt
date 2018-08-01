cmake_minimum_required(VERSION 2.4.0)

project(dht11)

set(CMAKE_CXX_FLAGS_DEBUG "-O0 -ggdb")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11")
set(WIRING_PI_LIBS -lwiringPi -lwiringPiDev)
set(COMMON_LIBS -lcommon-lib)

# Include header files
include_directories(include ../../../services/common/include ../common/include ../../../common/include ../../../thirdparty/rapidjson/include /usr/local/include/)
link_directories(${PROJECT_BINARY_DIR}/../../../lib)

# Find source files
file(GLOB SOURCES "*.cpp")

# Create shared library
add_library(${PROJECT_NAME} SHARED ${SOURCES})
target_link_libraries(${PROJECT_NAME} ${WIRING_PI_LIBS})
target_link_libraries(${PROJECT_NAME} ${COMMON_LIBS})
set_target_properties(${PROJECT_NAME} PROPERTIES SOVERSION 1)

# Install library
install(TARGETS ${PROJECT_NAME} DESTINATION foglamp/plugins/south/${PROJECT_NAME})
