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

# Find Python.h 3.5 header file
set(_PYTHON_3.5_INCLUDES /usr/include/python3.5m /usr/include/python3.5m)
list(APPEND _PYTHON_3.5_INCLUDES /usr/include/python3.5 /usr/include/python3.5)
find_path(Python3.5_INCLUDE NAMES Python.h PATHS ${_PYTHON_3.5_INCLUDES})
if (NOT Python3.5_INCLUDE)
        message(WARNING
        " Python 3.5 header file 'Python.h' not found in /usr/include. \n"
        " Target '${PROJECT_NAME}' filter is not built.")
        return()
else()
        message(STATUS "Found Python 3.5 header file 'Python.h' in " ${Python3.5_INCLUDE})
endif()

# Find Python 3.5 library
find_library(FoundPython_3.5 NAMES python3.5m python35m python3.5 python35)
if (NOT FoundPython_3.5)
        message(FATAL_ERROR "Python 3.5 library not found.")
        return()
else()
        message(STATUS "Found Python 3.5 library in " ${FoundPython_3.5})
endif()

# Include header files
include_directories(include ../services/common/include ../common/include ../thirdparty/rapidjson/include ../thirdparty/Simple-Web-Server)

# Add Python 3.5 header files
include_directories(${Python3.5_INCLUDE})

set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${PROJECT_BINARY_DIR}/../lib)

# Create shared library
add_library(${PROJECT_NAME} SHARED ${SOURCES})
target_link_libraries(${PROJECT_NAME} ${UUIDLIB})
target_link_libraries(${PROJECT_NAME} ${Boost_LIBRARIES})

# Add Python 3.5 library
target_link_libraries(${PROJECT_NAME} -lpython3.5m)

set_target_properties(${PROJECT_NAME} PROPERTIES SOVERSION 1)

# Install library
install(TARGETS ${PROJECT_NAME} DESTINATION foglamp/lib)
