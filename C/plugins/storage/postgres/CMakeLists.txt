cmake_minimum_required(VERSION 2.4.0)

project(postgres)

set(CMAKE_CXX_FLAGS_DEBUG "-O0 -ggdb")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11")
set(STORAGE_COMMON_LIB -lstorage-common-lib)

# Find source files
file(GLOB SOURCES *.cpp)

# Include header files
include_directories(include ../../../common/include ../../../services/common/include ../common/include)
include_directories(../../../thirdparty/rapidjson/include /usr/include/postgresql)
link_directories(${PROJECT_BINARY_DIR}/../../../lib)

# Create shared library
add_library(${PROJECT_NAME} SHARED ${SOURCES})
set_target_properties(${PROJECT_NAME} PROPERTIES SOVERSION 1)
target_link_libraries(${PROJECT_NAME} -lpq)
target_link_libraries(${PROJECT_NAME} ${STORAGE_COMMON_LIB})

# Install library
install(TARGETS ${PROJECT_NAME} DESTINATION foglamp/plugins/storage//${PROJECT_NAME})

# Install init.sql
install(FILES ${CMAKE_SOURCE_DIR}/scripts/plugins/storage/${PROJECT_NAME}/init.sql DESTINATION foglamp/plugins/storage//${PROJECT_NAME})
