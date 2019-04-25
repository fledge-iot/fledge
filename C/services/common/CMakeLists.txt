cmake_minimum_required(VERSION 2.6.0)

project(services-common-lib)

set(CMAKE_CXX_FLAGS_DEBUG "-O0 -ggdb")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11")
set(DLLIB -ldl)

# Find source files
file(GLOB SOURCES *.cpp)

# Find python3.x dev/lib package
#set(Python_ADDITIONAL_VERSIONS 3.6)
#find_package(PythonLibs 3 REQUIRED)
PKG_CHECK_MODULES(PYTHON REQUIRED python3)

message("PYTHON_LIBRARIES: ${PYTHON_LIBRARIES}")
message("PYTHON_INCLUDE_DIRS: ${PYTHON_INCLUDE_DIRS}")

# Include header files
include_directories(include ../../common/include ../../thirdparty/Simple-Web-Server  ../../thirdparty/rapidjson/include)

# Add Python 3.x header files
include_directories(${PYTHON_INCLUDE_DIRS})
link_directories(${PYTHON_LIBRARY_DIRS})

set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${PROJECT_BINARY_DIR}/../../lib)

# Create shared library
add_library(${PROJECT_NAME} SHARED ${SOURCES})
target_link_libraries(${PROJECT_NAME} ${DLLIB})

# Add Python 3.x library
target_link_libraries(${PROJECT_NAME} ${PYTHON_LIBRARIES})

set_target_properties(${PROJECT_NAME} PROPERTIES SOVERSION 1)

# Install library
install(TARGETS ${PROJECT_NAME} DESTINATION foglamp/lib)
