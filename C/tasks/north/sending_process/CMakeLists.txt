cmake_minimum_required (VERSION 2.8.8)
project (sending_process)

set(CMAKE_CXX_FLAGS_DEBUG "-O0 -ggdb")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11 -Wall -Wextra -Wsign-conversion")
set(DLLIB -ldl)
set(UUIDLIB -luuid)
set(COMMON_LIB common-lib)
set(SERVICE_COMMON_LIB services-common-lib)
set(PLUGINS_COMMON_LIB plugins-common-lib)

include_directories(. include ../../../thirdparty/Simple-Web-Server ../../../thirdparty/rapidjson/include  ../../../common/include ../../../services/common/include ../../../plugins/common/include)

find_package(Threads REQUIRED)

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

if(APPLE)
    set(OPENSSL_ROOT_DIR "/usr/local/opt/openssl")
endif()

file(GLOB sending_process_src "*.cpp")

# Find Python.h 3.5 header file
set(_PYTHON_3.5_INCLUDES /usr/include/python3.5m /usr/include/python3.5m)
list(APPEND _PYTHON_3.5_INCLUDES /usr/include/python3.5 /usr/include/python3.5)
find_path(Python3.5_INCLUDE NAMES Python.h PATHS ${_PYTHON_3.5_INCLUDES})
if (NOT Python3.5_INCLUDE)
        message(WARNING
        " Python 3.5 header file 'Python.h' not found in /usr/include. \n"
        " Target '${PROJECT_NAME}' filter is not built.")
        return()
else()
        message(STATUS "Found Python 3.5 header file 'Python.h' in " ${Python3.5_INCLUDE})
endif()

# Find Python 3.5 library
find_library(FoundPython_3.5 NAMES python3.5m python35m python3.5 python35)
if (NOT FoundPython_3.5)
        message(FATAL_ERROR "Python 3.5 library not found.")
        return()
else()
        message(STATUS "Found Python 3.5 library in " ${FoundPython_3.5})
endif()

# Add Python 3.5 header files
include_directories(${Python3.5_INCLUDE})

link_directories(${PROJECT_BINARY_DIR}/../../../lib)

add_executable(sending_process ${sending_process_src})
target_link_libraries(sending_process ${Boost_LIBRARIES})
target_link_libraries(sending_process ${CMAKE_THREAD_LIBS_INIT})
target_link_libraries(sending_process ${DLLIB})
target_link_libraries(sending_process ${UUIDLIB})
target_link_libraries(sending_process -lssl -lcrypto)

target_link_libraries(${PROJECT_NAME} ${COMMON_LIB})
target_link_libraries(${PROJECT_NAME} ${SERVICE_COMMON_LIB})
target_link_libraries(${PROJECT_NAME} ${PLUGINS_COMMON_LIB})

# Add Python 3.5 library
target_link_libraries(${PROJECT_NAME} -lpython3.5m)

install(TARGETS sending_process RUNTIME DESTINATION foglamp/tasks)

if(MSYS) #TODO: Is MSYS true when MSVC is true?
    target_link_libraries(sending_process ws2_32 wsock32)
    if(OPENSSL_FOUND)
        target_link_libraries(sending_process ws2_32 wsock32)
    endif()
endif()
