# Project configuration
project(RunTests)
cmake_minimum_required(VERSION 2.6)
set(CMAKE_CXX_FLAGS "-std=c++11 -O3")

set(UUIDLIB -luuid)
set(COMMONLIB -ldl)

# FogLAMP libraries
set(COMMON_LIB         common-lib)
set(SERVICE_COMMON_LIB services-common-lib)
set(PLUGINS_COMMON_LIB plugins-common-lib)
set(PLUGIN_POSTGRES    postgres)
set(STORAGE_COMMON_LIB storage-common-lib)
set(PG_LIB             pq)

# Locate GTest
find_package(GTest REQUIRED)

# Include files
include_directories(${GTEST_INCLUDE_DIRS})
include_directories(/usr/include/postgresql)
include_directories(../../../../../../C/common/include)
include_directories(../../../../../../C/services/common/include)
include_directories(../../../../../../C/plugins/storage/common/include)
include_directories(../../../../../../C/plugins/storage/postgres/include)
include_directories(../../../../../../C/thirdparty/rapidjson/include)

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

target_link_libraries(${PROJECT_NAME} ${GTEST_LIBRARIES} pthread)