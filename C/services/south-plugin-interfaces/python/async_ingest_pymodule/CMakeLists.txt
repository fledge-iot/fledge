cmake_minimum_required(VERSION 2.6.0)

project(async_ingest)

set(CMAKE_CXX_FLAGS_DEBUG "-O0 -ggdb")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11")
set(DLLIB -ldl)
set(COMMON_LIB common-lib)
set(SERVICE_COMMON_LIB services-common-lib)

# Find source files
file(GLOB SOURCES ingest_callback_pymodule.cpp ../pyobject_reading_parser.cpp)

# Find Python 3.5 or higher dev/lib/interp package
find_package(PythonLibs 3.5 REQUIRED)
find_package(PythonInterp 3.5 REQUIRED)

# Include header files
include_directories(include ../../../../common/include ../../../../services/common/include ../../../../services/south/include ../../../../thirdparty/rapidjson/include)

# Add Python 3.x header files
include_directories(${PYTHON_INCLUDE_DIRS})

link_directories(${PROJECT_BINARY_DIR}/../../../../lib)

set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${PROJECT_BINARY_DIR}/../../../../../../python)

# Create shared library
add_library(${PROJECT_NAME} SHARED ${SOURCES})

# Add Python 3.x library
target_link_libraries(${PROJECT_NAME} ${PYTHON_LIBRARIES})

target_link_libraries(${PROJECT_NAME} ${DLLIB})
target_link_libraries(${PROJECT_NAME} ${COMMON_LIB})
target_link_libraries(${PROJECT_NAME} ${SERVICE_COMMON_LIB})

set_target_properties(${PROJECT_NAME} PROPERTIES LINKER_LANGUAGE C)
set_target_properties(${PROJECT_NAME} PROPERTIES SOVERSION 1)
set_target_properties(${PROJECT_NAME} PROPERTIES VERSION 1)
set_target_properties(${PROJECT_NAME} PROPERTIES PREFIX "")

# Install libraries
install(TARGETS ${PROJECT_NAME} DESTINATION foglamp/python)
