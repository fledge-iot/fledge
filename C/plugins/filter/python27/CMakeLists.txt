cmake_minimum_required(VERSION 2.4.0)

project(python27)

# Find Python.h header file
find_path(Python2.7_INCLUDE NAMES Python.h PATHS /usr/include/python2.7 /usr/include/python27)
if (NOT Python2.7_INCLUDE)
	message(WARNING
	" Python 2.7 header file 'Python.h' not found in /usr/include. \n"
	" Target '${PROJECT_NAME}' filter is not built.")
	return()
else()
	message(STATUS "Found Python 2.7 header file 'Python.h' in " ${Python2.7_INCLUDE})
endif()

# Find Python 2.7 library
find_library(FoundPython_2.7 NAMES python2.7 python27)
if (NOT FoundPython_2.7)
	message(ERROR "Python 2.7 library not found.")
	return()
else()
	message(STATUS "Found Python 2.7 library in " ${FoundPython_2.7})
endif()

set(CMAKE_CXX_FLAGS_DEBUG "-O0 -ggdb")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11")

# Find source files
file(GLOB SOURCES *.cpp)
file(GLOB plugin_common_src "../../../plugins/filter/common/*.cpp" "../../../plugins/common/*.cpp")

# Include header files (first one is python2.7)
include_directories(${Python2.7_INCLUDE})
include_directories(include ../../../plugins/filter/common/include ../../../services/common/include ../../../thirdparty/Simple-Web-Server ../../../thirdparty/rapidjson/include ../../../common/include ../../../plugins/common/include)

# Create shared library
add_library(${PROJECT_NAME} SHARED ${SOURCES} ${plugin_common_src})
target_link_libraries(${PROJECT_NAME} -lssl -lcrypto)

# Add Python 2.7 library
target_link_libraries(${PROJECT_NAME} -lpython2.7)

set_target_properties(${PROJECT_NAME} PROPERTIES SOVERSION 1)

# Install library
install(TARGETS ${PROJECT_NAME} DESTINATION foglamp/plugins/filter/${PROJECT_NAME})
