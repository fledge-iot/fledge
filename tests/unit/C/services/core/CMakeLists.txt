set( CMAKE_VERBOSE_MAKEFILE on )

set(CMAKE_MODULE_PATH ${CMAKE_MODULE_PATH} ${CMAKE_CURRENT_SOURCE_DIR}/../..)

set(GCOVR_PATH "/home/nerd039/.local/bin/gcovr")

# Project configuration
project(RunTests)
cmake_minimum_required(VERSION 2.6)

set(CMAKE_CXX_FLAGS "-std=c++11 -O0 -ggdb --coverage")
set(UUIDLIB -luuid)
set(COMMONLIB -ldl)
 
include(CodeCoverage)
append_coverage_compiler_flags()

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
include_directories(../../../../../C/services/common/include)
include_directories(../../../../../C/services/core/include)
include_directories(../../../../../C/thirdparty/rapidjson/include)
include_directories(../../../../../C/thirdparty/Simple-Web-Server)

set(COMMON_LIB common-lib)
set(SERVICE_COMMON_LIB services-common-lib)

file(GLOB test_sources "../../../../../C/services/core/*.cpp")
file(GLOB unittests "*.cpp")
 
# Find python3.x dev/lib package
find_package(PkgConfig REQUIRED)
if(${CMAKE_VERSION} VERSION_LESS "3.12.0") 
    pkg_check_modules(PYTHON REQUIRED python3)
else()
    find_package(Python3 COMPONENTS Interpreter Development)
endif()

# Add Python 3.x header files
if(${CMAKE_VERSION} VERSION_LESS "3.12.0") 
    include_directories(${PYTHON_INCLUDE_DIRS})
else()
    include_directories(${Python3_INCLUDE_DIRS})
endif()

if(${CMAKE_VERSION} VERSION_LESS "3.12.0") 
    link_directories(${PYTHON_LIBRARY_DIRS})
else()
    link_directories(${Python3_LIBRARY_DIRS})
endif()

link_directories(${PROJECT_BINARY_DIR}/../../../lib)

# Link runTests with what we want to test and the GTest and pthread library
add_executable(RunTests ${test_sources} ${unittests})
target_link_libraries(RunTests ${GTEST_LIBRARIES} pthread)
target_link_libraries(RunTests  ${Boost_LIBRARIES})
target_link_libraries(RunTests  ${UUIDLIB})
target_link_libraries(RunTests  ${COMMONLIB})
target_link_libraries(RunTests -lssl -lcrypto -lz)
target_link_libraries(RunTests ${COMMON_LIB})
target_link_libraries(RunTests ${SERVICE_COMMON_LIB})

# Add Python 3.x library
if(${CMAKE_VERSION} VERSION_LESS "3.12.0") 
    target_link_libraries(RunTests ${PYTHON_LIBRARIES})
else()
    target_link_libraries(RunTests ${Python3_LIBRARIES})
endif()

setup_target_for_coverage_gcovr_html(
            NAME CoverageHtml
            EXECUTABLE ${PROJECT_NAME}
            DEPENDENCIES ${PROJECT_NAME}
    )

