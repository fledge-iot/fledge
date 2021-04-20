cmake_minimum_required(VERSION 2.6.0)

project(north-plugin-python-interface)

set(CMAKE_CXX_FLAGS_DEBUG "-O0 -ggdb")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11")
set(DLLIB -ldl)
set(COMMON_LIB common-lib)
set(SERVICE_COMMON_LIB services-common-lib)

# Find source files
file(GLOB SOURCES python_plugin_interface.cpp ../../common-plugin-interfaces/python/pyobject_reading_parser.cpp)

# Find Python.h 3.x dev/lib package
if(${CMAKE_VERSION} VERSION_LESS "3.12.0") 
    pkg_check_modules(PYTHON REQUIRED python3)
else()
    find_package(Python COMPONENTS Interpreter Development)
endif()

# Include header files
include_directories(include ../../../common/include ../../../services/common/include ../../../services/north/include ../../../thirdparty/rapidjson/include)
include_directories(../../../services/common-plugin-interfaces/python/include)

# Add Python 3.x header files
if(${CMAKE_VERSION} VERSION_LESS "3.12.0") 
    include_directories(${PYTHON_INCLUDE_DIRS})
else()
    include_directories(${Python_INCLUDE_DIRS})
endif()

if(${CMAKE_VERSION} VERSION_LESS "3.12.0") 
    link_directories(${PYTHON_LIBRARY_DIRS})
else()
    link_directories(${PYTHON_LIBRARY_DIRS})
endif()

set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${PROJECT_BINARY_DIR}/../../../lib)

# Create shared library
add_library(${PROJECT_NAME} SHARED ${SOURCES})
target_link_libraries(${PROJECT_NAME} ${DLLIB})
target_link_libraries(${PROJECT_NAME} ${COMMON_LIB})
target_link_libraries(${PROJECT_NAME} ${SERVICE_COMMON_LIB})

# Add Python 3.x library
if(${CMAKE_VERSION} VERSION_LESS "3.12.0") 
    target_link_libraries(${PROJECT_NAME} ${PYTHON_LIBRARIES})
else()
    target_link_libraries(${PROJECT_NAME} ${Python_LIBRARIES})
endif()

set_target_properties(${PROJECT_NAME} PROPERTIES SOVERSION 1)

# Install library
install(TARGETS ${PROJECT_NAME} DESTINATION fledge/lib)
