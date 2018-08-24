cmake_minimum_required(VERSION 2.4.0)

project(scale)

set(CMAKE_CXX_FLAGS_DEBUG "-O0 -ggdb")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11")

set(COMMON_LIBS -lcommon-lib)

# Find source files
file(GLOB SOURCES *.cpp)
file(GLOB plugin_filter_common_src "../../../plugins/filter/common/*.cpp")

# Include header files
include_directories(include ../../../plugins/filter/common/include ../../../services/common/include ../../../thirdparty/Simple-Web-Server ../../../thirdparty/rapidjson/include ../../../common/include ../../../plugins/common/include)

# Create shared library
link_directories(${PROJECT_BINARY_DIR}/../../../lib)
add_library(${PROJECT_NAME} SHARED ${SOURCES} ${plugin_filter_common_src})
target_link_libraries(${PROJECT_NAME} -lssl -lcrypto)
target_link_libraries(${PROJECT_NAME} ${COMMON_LIBS})
set_target_properties(${PROJECT_NAME} PROPERTIES SOVERSION 1)

# Install library
install(TARGETS ${PROJECT_NAME} DESTINATION foglamp/plugins/filter/${PROJECT_NAME})
