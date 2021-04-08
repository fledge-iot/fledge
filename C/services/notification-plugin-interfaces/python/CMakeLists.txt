cmake_minimum_required(VERSION 2.6.0)

project(notification-plugin-python-interface)

set(CMAKE_CXX_FLAGS_DEBUG "-O0 -ggdb")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11")
set(DLLIB -ldl)
set(COMMON_LIB common-lib)
set(SERVICE_COMMON_LIB services-common-lib)

# Find source files
file(GLOB SOURCES python_plugin_interface.cpp)

# Find Python.h 3.x dev/lib package
find_package(Python COMPONENTS Interpreter Development)

# Include header files
include_directories(include ../../../common/include ../../../services/common/include ../../../services/south/include ../../../thirdparty/rapidjson/include)
include_directories(../../../services/common-plugin-interfaces/python/include)

# Add Python 3.x header files
include_directories(${Python_INCLUDE_DIRS})

link_directories(${Python_LIBRARY_DIRS})

set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${PROJECT_BINARY_DIR}/../../../lib)

# Create shared library
add_library(${PROJECT_NAME} SHARED ${SOURCES})
target_link_libraries(${PROJECT_NAME} ${DLLIB})
target_link_libraries(${PROJECT_NAME} ${COMMON_LIB})
target_link_libraries(${PROJECT_NAME} ${SERVICE_COMMON_LIB})

# Add Python 3.x library
target_link_libraries(${PROJECT_NAME} ${Python_LIBRARIES})

set_target_properties(${PROJECT_NAME} PROPERTIES SOVERSION 1)

# Install library
install(TARGETS ${PROJECT_NAME} DESTINATION fledge/lib)
