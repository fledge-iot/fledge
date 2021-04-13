cmake_minimum_required(VERSION 2.6.0)

project(filter_ingest)

set(CMAKE_CXX_FLAGS_DEBUG "-O0 -ggdb")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11")
set(DLLIB -ldl)
set(COMMON_LIB common-lib)
set(SERVICE_COMMON_LIB services-common-lib)

# Find source files
file(GLOB SOURCES ingest_callback_pymodule.cpp ../../../common-plugin-interfaces/python/pyobject_reading_parser.cpp)

# Find Python 3.5 or higher dev/lib/interp package
#find_package(PythonInterp 3.5 REQUIRED)
if(${CMAKE_VERSION} VERSION_LESS "3.12.0") 
    pkg_check_modules(PYTHON REQUIRED python3)
else()
    find_package(Python COMPONENTS Interpreter Development)
endif()

# Include header files
include_directories(include)
include_directories(../../../../common/include)
include_directories(../../../../services/common/include)
include_directories(../../../../services/south/include)
include_directories(../../../../thirdparty/rapidjson/include)

# Add Python 3.x header files
if(${CMAKE_VERSION} VERSION_LESS "3.12.0") 
    include_directories(${PYTHON_INCLUDE_DIRS})
else()
    include_directories(${Python_INCLUDE_DIRS})
endif()

if(${CMAKE_VERSION} VERSION_LESS "3.12.0") 
    link_directories(${PYTHON_LIBRARY_DIRS})
else()
    link_directories(${Python_LIBRARY_DIRS})
endif()
link_directories(${PROJECT_BINARY_DIR}/../../../../lib)

set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${PROJECT_BINARY_DIR}/../../../../../../python)

# Create shared library
add_library(${PROJECT_NAME} SHARED ${SOURCES})

# Add Python 3.x library
if(${CMAKE_VERSION} VERSION_LESS "3.12.0") 
    target_link_libraries(${PROJECT_NAME} ${PYTHON_LIBRARIES})
else()
    target_link_libraries(${PROJECT_NAME} ${Python_LIBRARIES})
endif()

target_link_libraries(${PROJECT_NAME} ${DLLIB})
target_link_libraries(${PROJECT_NAME} ${COMMON_LIB})
target_link_libraries(${PROJECT_NAME} ${SERVICE_COMMON_LIB})

set_target_properties(${PROJECT_NAME} PROPERTIES LINKER_LANGUAGE C)
set_target_properties(${PROJECT_NAME} PROPERTIES SOVERSION 1)
set_target_properties(${PROJECT_NAME} PROPERTIES VERSION 1)
set_target_properties(${PROJECT_NAME} PROPERTIES PREFIX "")

# Install libraries
install(TARGETS ${PROJECT_NAME} DESTINATION fledge/python)
