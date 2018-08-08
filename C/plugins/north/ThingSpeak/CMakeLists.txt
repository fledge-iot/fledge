cmake_minimum_required(VERSION 2.4.0)

project(ThingSpeak)

set(CMAKE_CXX_FLAGS_DEBUG "-O0 -ggdb")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11")
set(PLUGINS_COMMON_LIBS -lplugins-common-lib)
set(COMMON_LIBS -lcommon-lib -lssl -lcrypto)

# Find source files
file(GLOB SOURCES *.cpp)

# Include header files
include_directories(include ../../../services/common/include ../../../thirdparty/Simple-Web-Server ../../../thirdparty/rapidjson/include ../../../common/include ../../../plugins/common/include)
link_directories(${PROJECT_BINARY_DIR}/../../../lib)

# Create shared library
add_library(${PROJECT_NAME} SHARED ${SOURCES})
target_link_libraries(${PROJECT_NAME} ${COMMON_LIBS})
target_link_libraries(${PROJECT_NAME} ${PLUGINS_COMMON_LIBS})
set_target_properties(${PROJECT_NAME} PROPERTIES SOVERSION 1)

# Install library
install(TARGETS ${PROJECT_NAME} DESTINATION foglamp/plugins/north/${PROJECT_NAME})
