# Project configuration
project(RunTests)
cmake_minimum_required(VERSION 2.6)
set(CMAKE_CXX_FLAGS "-std=c++11 -O3")

# libraries
set(PG_LIB     pq)
set(LIBCURL_LIB -lcurl)

# Fledge libraries
set(COMMON_LIB         common-lib)
set(SERVICE_COMMON_LIB services-common-lib)
set(PLUGINS_COMMON_LIB plugins-common-lib)
set(PLUGIN_POSTGRES    postgres)
set(STORAGE_COMMON_LIB storage-common-lib)

# Handle Postgres on RedHat/CentOS
set(CMAKE_MODULE_PATH ${CMAKE_MODULE_PATH} "${CMAKE_CURRENT_SOURCE_DIR}")
include(CheckRhPg)

# Locate GTest
find_package(GTest REQUIRED)

# Include files
include_directories(${GTEST_INCLUDE_DIRS})
include_directories(../../../../../../C/common/include)
include_directories(../../../../../../C/services/common/include)
include_directories(../../../../../../C/plugins/storage/common/include)
include_directories(../../../../../../C/plugins/storage/postgres/include)
include_directories(../../../../../../C/thirdparty/rapidjson/include)

# Handle Postgres on RedHat/CentOS
if(${RH_POSTGRES_FOUND} EQUAL 1)

    include_directories(${RH_POSTGRES_INCLUDE})
    link_directories(${RH_POSTGRES_LIB64})
else()
    include_directories(/usr/include/postgresql)
endif()

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

# Source files
file(GLOB test_sources tests.cpp)

# Exe creation
link_directories(
        ${PROJECT_BINARY_DIR}/../../../../lib
)

add_executable(${PROJECT_NAME} ${test_sources})

target_link_libraries(${PROJECT_NAME} ${COMMON_LIB})
target_link_libraries(${PROJECT_NAME} ${SERVICE_COMMON_LIB})
target_link_libraries(${PROJECT_NAME} ${PLUGINS_COMMON_LIB})

target_link_libraries(${PROJECT_NAME} ${PLUGIN_POSTGRES})
target_link_libraries(${PROJECT_NAME} ${STORAGE_COMMON_LIB})
target_link_libraries(${PROJECT_NAME} ${PG_LIB})
target_link_libraries(${PROJECT_NAME} ${LIBCURL_LIB})

target_link_libraries(${PROJECT_NAME} ${GTEST_LIBRARIES} pthread)
# Add Python 3.x library
if(${CMAKE_VERSION} VERSION_LESS "3.12.0")
	target_link_libraries(${PROJECT_NAME} ${PYTHON_LIBRARIES})
else()
	target_link_libraries(${PROJECT_NAME} ${Python3_LIBRARIES})
endif()
