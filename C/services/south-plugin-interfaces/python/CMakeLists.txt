cmake_minimum_required(VERSION 2.6.0)

project(south-plugin-python-interface)

set(CMAKE_CXX_FLAGS_DEBUG "-O0 -ggdb")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11")
set(DLLIB -ldl)
set(COMMON_LIB common-lib)
set(SERVICE_COMMON_LIB services-common-lib)

# Find source files
file(GLOB SOURCES python_plugin_interface.cpp pyobject_reading_parser.cpp)

# Find Python.h 3.x dev/lib package
find_package(PythonLibs 3 REQUIRED)

# Include header files
include_directories(include ../../../common/include ../../../services/common/include ../../../services/south/include ../../../thirdparty/rapidjson/include)

# Add Python 3.x header files
include_directories(${PYTHON_INCLUDE_DIRS})

set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${PROJECT_BINARY_DIR}/../../../lib)

# Create shared library
add_library(${PROJECT_NAME} SHARED ${SOURCES})
target_link_libraries(${PROJECT_NAME} ${DLLIB})
target_link_libraries(${PROJECT_NAME} ${COMMON_LIB})
target_link_libraries(${PROJECT_NAME} ${SERVICE_COMMON_LIB})

# Add Python 3.x library
target_link_libraries(${PROJECT_NAME} ${PYTHON_LIBRARIES})

set_target_properties(${PROJECT_NAME} PROPERTIES SOVERSION 1)

# Install library
install(TARGETS ${PROJECT_NAME} DESTINATION foglamp/lib)
