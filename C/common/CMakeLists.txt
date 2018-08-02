cmake_minimum_required(VERSION 2.4.0)

project(common-lib)

set(CMAKE_CXX_FLAGS_DEBUG "-O0 -ggdb")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11")
set(UUIDLIB -luuid)

set(BOOST_COMPONENTS system thread)
# Late 2017 TODO: remove the following checks and always use std::regex
if("${CMAKE_CXX_COMPILER_ID}" STREQUAL "GNU")
    if (CMAKE_CXX_COMPILER_VERSION VERSION_LESS 4.9)
        set(BOOST_COMPONENTS ${BOOST_COMPONENTS} regex)
        set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -DUSE_BOOST_REGEX")
    endif()
endif()
find_package(Boost 1.53.0 COMPONENTS ${BOOST_COMPONENTS} REQUIRED)
include_directories(SYSTEM ${Boost_INCLUDE_DIR})

# Find source files
file(GLOB SOURCES *.cpp)

# Include header files
include_directories(include ../services/common/include ../common/include ../thirdparty/rapidjson/include ../thirdparty/Simple-Web-Server)

set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${PROJECT_BINARY_DIR}/../lib)

# Create shared library
add_library(${PROJECT_NAME} SHARED ${SOURCES})
target_link_libraries(${PROJECT_NAME} ${UUIDLIB})
target_link_libraries(${PROJECT_NAME} ${Boost_LIBRARIES})
set_target_properties(${PROJECT_NAME} PROPERTIES SOVERSION 1)

# Install library
install(TARGETS ${PROJECT_NAME} DESTINATION foglamp/lib)
