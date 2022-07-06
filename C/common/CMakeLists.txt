cmake_minimum_required(VERSION 2.4.0)

if(COMMAND cmake_policy)
    cmake_policy(SET CMP0003 NEW)
endif(COMMAND cmake_policy)

# Get the os name
execute_process(COMMAND bash -c "cat /etc/os-release | grep -w ID | cut -f2 -d'='"
                                OUTPUT_VARIABLE
                                OS_NAME
                                OUTPUT_STRIP_TRAILING_WHITESPACE)

if( POLICY CMP0007 )
    cmake_policy( SET CMP0007 NEW )
endif()
project(common-lib)

set(CMAKE_CXX_FLAGS_DEBUG "-O0 -ggdb")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11")
set(UUIDLIB -luuid)

set(BOOST_COMPONENTS system thread)
# Late 2017 TODO: remove the following checks and always use std::regex
if("${CMAKE_CXX_COMPILER_ID}" STREQUAL "GNU")
    if (CMAKE_CXX_COMPILER_VERSION VERSION_LESS 4.9)
        set(BOOST_COMPONENTS ${BOOST_COMPONENTS} regex)
        set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -DUSE_BOOST_REGEX")
    endif()
endif()
find_package(Boost 1.53.0 COMPONENTS ${BOOST_COMPONENTS} REQUIRED)
include_directories(SYSTEM ${Boost_INCLUDE_DIR})

# Find python3.x dev/lib package
find_package(PkgConfig REQUIRED)
if(${CMAKE_VERSION} VERSION_LESS "3.12.0")
    pkg_check_modules(PYTHON REQUIRED python3)
else()
    if("${OS_NAME}" STREQUAL "mendel")
        # We will explicitly set include path later for NumPy.
        find_package(Python3 REQUIRED COMPONENTS Interpreter Development )
    else()
        find_package(Python3 REQUIRED COMPONENTS Interpreter Development NumPy)
    endif()
endif()

# Find source files
file(GLOB SOURCES *.cpp)

# Include header files
include_directories(include ../services/common/include ../common/include ../thirdparty/rapidjson/include ../thirdparty/Simple-Web-Server)

# Add Python 3.x header files
if(${CMAKE_VERSION} VERSION_LESS "3.12.0")
    include_directories(${PYTHON_INCLUDE_DIRS})
else()
    if("${OS_NAME}" STREQUAL "mendel")
        # The following command gets the location of NumPy.
        execute_process(
            COMMAND python3
                -c "import numpy; print(numpy.get_include())"
                OUTPUT_VARIABLE Python3_NUMPY_INCLUDE_DIRS
                OUTPUT_STRIP_TRAILING_WHITESPACE
        )
        # Now we can add include directories as usual.
        include_directories(${Python3_INCLUDE_DIRS} ${Python3_NUMPY_INCLUDE_DIRS})
    else()
        include_directories(${Python3_INCLUDE_DIRS} ${Python3_NUMPY_INCLUDE_DIRS})
    endif()
endif()

if(${CMAKE_VERSION} VERSION_LESS "3.12.0")
    link_directories(${PYTHON_LIBRARY_DIRS})
else()
    link_directories(${Python3_LIBRARY_DIRS})
endif()

set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${PROJECT_BINARY_DIR}/../lib)

# Create shared library
add_library(${PROJECT_NAME} SHARED ${SOURCES})
# Add Python 3.5 library
if(${CMAKE_VERSION} VERSION_LESS "3.12.0")
    target_link_libraries(${PROJECT_NAME} ${PYTHON_LIBRARIES})
else()
    if("${OS_NAME}" STREQUAL "mendel")
        target_link_libraries(${PROJECT_NAME} ${Python3_LIBRARIES})
    else()
	    target_link_libraries(${PROJECT_NAME} ${Python3_LIBRARIES} Python3::NumPy)
	endif()
endif()

target_link_libraries(${PROJECT_NAME} ${UUIDLIB})
target_link_libraries(${PROJECT_NAME} ${Boost_LIBRARIES})
target_link_libraries(${PROJECT_NAME} -lcrypto)

set_target_properties(${PROJECT_NAME} PROPERTIES SOVERSION 1)

# Install library
install(TARGETS ${PROJECT_NAME} DESTINATION fledge/lib)
