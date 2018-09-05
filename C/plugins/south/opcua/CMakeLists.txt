cmake_minimum_required(VERSION 2.4.0)

project(opcua)

set(CMAKE_CXX_FLAGS_DEBUG "-O0 -ggdb")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11")
set(COMMON_LIBS -lcommon-lib)
set(ADDITIONAL_LINK_LIBRARIES pthread dl)
set(OPCUALIBS opcuaprotocol opcuacore opcuaclient)
# Find source files
file(GLOB SOURCES *.cpp)

# Include header files
include_directories(include ../../../services/common/include ../common/include ../../../common/include ../../../thirdparty/rapidjson/include ~/freeopcua/include)
link_directories(${PROJECT_BINARY_DIR}/../../../lib ~/freeopcua/build/lib)

# Create shared library
add_library(${PROJECT_NAME} SHARED ${SOURCES})
target_link_libraries(${PROJECT_NAME} ${COMMON_LIBS})
target_link_libraries(${PROJECT_NAME} ${ADDITIONAL_LINK_LIBRARIES})
target_link_libraries(${PROJECT_NAME} ${OPCUALIBS})

set_target_properties(${PROJECT_NAME} PROPERTIES SOVERSION 1)

# Install library
install(TARGETS ${PROJECT_NAME} DESTINATION foglamp/plugins/south/${PROJECT_NAME})
