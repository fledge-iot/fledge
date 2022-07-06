cmake_minimum_required(VERSION 2.6)

set(CMAKE_MODULE_PATH ${CMAKE_MODULE_PATH} ${CMAKE_CURRENT_SOURCE_DIR}/..)
set(GCOVR_PATH "$ENV{HOME}/.local/bin/gcovr")

project(RunTests)

include(CodeCoverage)
append_coverage_compiler_flags()

set(CMAKE_CXX_FLAGS "-std=c++11 -O0")
set(UUIDLIB -luuid)
set(COMMONLIB -ldl)
set(LIBCURL_LIB -lcurl)

# Locate GTest
find_package(GTest REQUIRED)
include_directories(${GTEST_INCLUDE_DIRS})

EXECUTE_PROCESS( COMMAND grep -o ^NAME=.* /etc/os-release COMMAND cut -f2 -d\" COMMAND sed s/\"//g OUTPUT_VARIABLE os_name )
EXECUTE_PROCESS( COMMAND grep -o ^VERSION_ID=.* /etc/os-release COMMAND cut -f2 -d\" COMMAND sed s/\"//g OUTPUT_VARIABLE os_version )

if ( ( ${os_name} MATCHES "Red Hat" OR ${os_name} MATCHES "CentOS") AND ( ${os_version} MATCHES "7" ) )
    add_definitions(-DRHEL_CENTOS_7=1)
    message( "System is RHEL/CentOS 7, tests on regex are skipped" )
endif()

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

include_directories(../../../../C/common/include)
include_directories(../../../../C/plugins/common/include)
include_directories(../../../../C/services/common/include)
include_directories(../../../../C/thirdparty/rapidjson/include)
include_directories(../../../../C/thirdparty/Simple-Web-Server)

set(COMMON_LIB common-lib)
set(SERVICE_COMMON_LIB services-common-lib)
set(PLUGINS_COMMON_LIB plugins-common-lib)

file(GLOB unittests "*.cpp")
 
# Find python3.x dev/lib package
find_package(PkgConfig REQUIRED)
if(${CMAKE_VERSION} VERSION_LESS "3.12.0") 
    pkg_check_modules(PYTHON REQUIRED python3)
else()
    find_package(Python3 REQUIRED COMPONENTS Interpreter Development NumPy)
endif()

# Add Python 3.x header files
if(${CMAKE_VERSION} VERSION_LESS "3.12.0") 
    include_directories(${PYTHON_INCLUDE_DIRS})
else()
    include_directories(${Python3_INCLUDE_DIRS} ${Python3_NUMPY_INCLUDE_DIRS})
endif()

if(${CMAKE_VERSION} VERSION_LESS "3.12.0") 
    link_directories(${PYTHON_LIBRARY_DIRS})
else()
    link_directories(${Python3_LIBRARY_DIRS})
endif()

link_directories(${PROJECT_BINARY_DIR}/../../lib)

# Link runTests with what we want to test and the GTest and pthread library
add_executable(RunTests ${unittests})
target_link_libraries(RunTests ${GTEST_LIBRARIES} pthread)
target_link_libraries(RunTests  ${Boost_LIBRARIES})
target_link_libraries(RunTests  ${UUIDLIB})
target_link_libraries(RunTests  ${COMMONLIB})
target_link_libraries(RunTests  ${LIBCURL_LIB})
target_link_libraries(RunTests -lssl -lcrypto -lz)
target_link_libraries(RunTests ${COMMON_LIB})
target_link_libraries(RunTests ${SERVICE_COMMON_LIB})
target_link_libraries(RunTests ${PLUGINS_COMMON_LIB})

# Add Python 3.x library
if(${CMAKE_VERSION} VERSION_LESS "3.12.0") 
    target_link_libraries(RunTests ${PYTHON_LIBRARIES})
else()
	target_link_libraries(${PROJECT_NAME} ${Python3_LIBRARIES} Python3::NumPy)
endif()

setup_target_for_coverage_gcovr_html(
            NAME CoverageHtml
            EXECUTABLE ${PROJECT_NAME}
            DEPENDENCIES ${PROJECT_NAME}
    )

