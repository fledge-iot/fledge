cmake_minimum_required (VERSION 2.8.8)
project (Core)

set(CMAKE_CXX_FLAGS_DEBUG "-O0 -ggdb")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11 -Wall -Wextra -Wsign-conversion")
set(DLLIB -ldl)
set(UUIDLIB -luuid)
set(COMMON_LIB -lcommon-lib)
set(SERVICE_COMMON_LIB -lservices-common-lib)

include_directories(. include ../../thirdparty/Simple-Web-Server ../../thirdparty/rapidjson/include  ../common/include ../../common/include)

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

file(GLOB core_src "*.cpp")

link_directories(${PROJECT_BINARY_DIR}/../../lib)

# Create static library
add_library(core ${core_src})
target_link_libraries(core ${Boost_LIBRARIES})
target_link_libraries(core ${CMAKE_THREAD_LIBS_INIT})
target_link_libraries(core ${DLLIB})
target_link_libraries(core ${UUIDLIB})
target_link_libraries(core -lssl -lcrypto)
target_link_libraries(core ${COMMON_LIB})
target_link_libraries(core ${SERVICE_COMMON_LIB})

if(MSYS) #TODO: Is MSYS true when MSVC is true?
    target_link_libraries(storage ws2_32 wsock32)
    if(OPENSSL_FOUND)
        target_link_libraries(storage ws2_32 wsock32)
    endif()
endif()
