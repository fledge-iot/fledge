cmake_minimum_required(VERSION 2.6)

set(CMAKE_CXX_FLAGS "-std=c++11 -O3")
set(UUIDLIB -luuid)
set(COMMONLIB -ldl)
 
EXECUTE_PROCESS( COMMAND grep -o ^NAME=.* /etc/os-release COMMAND cut -f2 -d\" COMMAND sed s/\"//g OUTPUT_VARIABLE os_name )
EXECUTE_PROCESS( COMMAND grep -o ^VERSION_ID=.* /etc/os-release COMMAND cut -f2 -d\" COMMAND sed s/\"//g OUTPUT_VARIABLE os_version )

if ( ( ${os_name} MATCHES "Red Hat" OR ${os_name} MATCHES "CentOS") AND ( ${os_version} MATCHES "7" ) )
        add_compile_options(-D RHEL_CENTOS_7)
        message( "System is RHEL/CentOS 7" )
else()
        message( "System is not RHEL/CentOS 7" )
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

# Find python3.x dev/lib package
find_package(PkgConfig REQUIRED)
if(${CMAKE_VERSION} VERSION_LESS "3.12.0") 
    pkg_check_modules(PYTHON REQUIRED python3)
else()
    find_package(Python COMPONENTS Interpreter Development)
endif()

include_directories(../../../C/common/include)
include_directories(../../../C/plugins/common/include)
include_directories(../../../C/plugins/north/OMF/include)
include_directories(../../../C/services/common/include)
include_directories(../../../C/thirdparty/rapidjson/include)
include_directories(../../../C/thirdparty/Simple-Web-Server)
include_directories(../../../C/plugins/storage/common/include)

# Add Python 3.x header files
if(${CMAKE_VERSION} VERSION_LESS "3.12.0") 
    include_directories(${PYTHON_INCLUDE_DIRS})
else()
    include_directories(${Python_INCLUDE_DIRS})
endif()

set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${PROJECT_BINARY_DIR}/../lib)

# Find source files
file(GLOB COMMON_LIB_SOURCES ../../../C/common/*.cpp)

# Create shared library
add_library(common-lib SHARED ${COMMON_LIB_SOURCES})
target_link_libraries(common-lib ${UUIDLIB})
target_link_libraries(common-lib ${Boost_LIBRARIES})
set_target_properties(common-lib PROPERTIES SOVERSION 1)


# Find source files
file(GLOB SERVICES_COMMON_LIB_SOURCES ../../../C/services/common/*.cpp)

# Create shared library
add_library(services-common-lib SHARED ${SERVICES_COMMON_LIB_SOURCES})
target_link_libraries(services-common-lib ${COMMONLIB})
set_target_properties(services-common-lib PROPERTIES SOVERSION 1)


# Find source files
file(GLOB PLUGINS_COMMON_LIB_SOURCES ../../../C/plugins/common/*.cpp)

# Create shared library
set(LIBCURL_LIB -lcurl)

add_library(plugins-common-lib SHARED ${PLUGINS_COMMON_LIB_SOURCES})
target_link_libraries(plugins-common-lib ${Boost_LIBRARIES} common-lib services-common-lib z ssl crypto)
target_link_libraries(plugins-common-lib ${LIBCURL_LIB})

set_target_properties(plugins-common-lib PROPERTIES SOVERSION 1)

#
# OMF library
#
set(LIB_NAME OMF)
file(GLOB OMF_LIB_SOURCES
        ../../../C/plugins/north/OMF/omf.cpp
        ../../../C/plugins/north/OMF/omfhints.cpp)

add_library(${LIB_NAME}  SHARED ${OMF_LIB_SOURCES})
target_link_libraries(${LIB_NAME}
                        common-lib
                        plugins-common-lib
                        ssl
                        crypto)

set_target_properties(${LIB_NAME}  PROPERTIES SOVERSION 1)

#
# storage-common-lib
#
set(LIB_NAME storage-common-lib)
set(DLLIB -ldl)

# Find source files
file(GLOB STORAGE_COMMON_LIB_SOURCE ../../../C/plugins/storage/common/*.cpp)

# Create shared library
add_library(${LIB_NAME} SHARED ${STORAGE_COMMON_LIB_SOURCE})
target_link_libraries(${LIB_NAME} ${DLLIB})
set_target_properties(${LIB_NAME} PROPERTIES SOVERSION 1)

add_subdirectory(cmake_pg)
add_subdirectory(cmake_sqlite)
add_subdirectory(cmake_sqlitelb)
add_subdirectory(cmake_sqliteM)
