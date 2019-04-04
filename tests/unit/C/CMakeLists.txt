cmake_minimum_required(VERSION 2.6)

set(CMAKE_CXX_FLAGS "-std=c++11 -O3")
set(UUIDLIB -luuid)
set(COMMONLIB -ldl)
 
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
find_package(PythonLibs 3 REQUIRED)

include_directories(../../../C/common/include)
include_directories(../../../C/plugins/common/include)
include_directories(../../../C/services/common/include)
include_directories(../../../C/thirdparty/rapidjson/include)
include_directories(../../../C/thirdparty/Simple-Web-Server)
include_directories(../../../C/plugins/storage/common/include)

# Add Python 3.x header files
include_directories(${PYTHON_INCLUDE_DIRS})

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
target_link_libraries(services-common-lib ${PYTHON_LIBRARIES})
set_target_properties(services-common-lib PROPERTIES SOVERSION 1)


# Find source files
file(GLOB PLUGINS_COMMON_LIB_SOURCES ../../../C/plugins/common/*.cpp)

# Create shared library
add_library(plugins-common-lib SHARED ${PLUGINS_COMMON_LIB_SOURCES})
target_link_libraries(plugins-common-lib ${Boost_LIBRARIES} common-lib services-common-lib z ssl crypto)

set_target_properties(plugins-common-lib PROPERTIES SOVERSION 1)

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
