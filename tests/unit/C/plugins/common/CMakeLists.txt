cmake_minimum_required(VERSION 2.6)

set(CMAKE_CXX_FLAGS "-std=c++11 -O3")
set(UUIDLIB -luuid)
set(COMMONLIB -ldl)
 
# Locate GTest
find_package(GTest REQUIRED)
include_directories(${GTEST_INCLUDE_DIRS})

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

include_directories(../../../../../C/common/include)
include_directories(../../../../../C/plugins/common/include)
include_directories(../../../../../C/services/common/include)
include_directories(../../../../../C/thirdparty/rapidjson/include)
include_directories(../../../../../C/thirdparty/Simple-Web-Server)

file(GLOB common_sources "../../../../../C/common/*.cpp")
file(GLOB plugin_common_sources "../../../../../C/plugins/common/*.cpp")
file(GLOB services_common_sources "../../../../../C/services/common/*.cpp")
file(GLOB unittests "*.cpp")
 
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

# Add Python 3.5 header files
include_directories(${Python3.5_INCLUDE})

# Link runTests with what we want to test and the GTest and pthread library
add_executable(RunTests ${common_sources} ${plugin_common_sources} ${services_common_sources} ${unittests})
target_link_libraries(RunTests ${GTEST_LIBRARIES} pthread)
target_link_libraries(RunTests  ${Boost_LIBRARIES})
target_link_libraries(RunTests  ${UUIDLIB})
target_link_libraries(RunTests  ${COMMONLIB})
target_link_libraries(RunTests  -lssl -lcrypto -lz)

# Add Python 3.5 library
target_link_libraries(RunTests -lpython3.5m)

