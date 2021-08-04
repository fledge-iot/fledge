cmake_minimum_required (VERSION 2.8.8)
project (purge_system)

set(CMAKE_CXX_FLAGS_DEBUG "-O0 -ggdb")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11 -Wall -Wextra -Wsign-conversion")
set(COMMON_LIB common-lib)
set(PLUGINS_COMMON_LIB plugins-common-lib)

find_package(Threads REQUIRED)

set(BOOST_COMPONENTS system thread)

find_package(Boost 1.53.0 COMPONENTS ${BOOST_COMPONENTS} REQUIRED)
include_directories(SYSTEM ${Boost_INCLUDE_DIR})

include_directories(.)
include_directories(include)
include_directories(../../thirdparty/Simple-Web-Server)
include_directories(../../thirdparty/rapidjson/include)
include_directories(../../common/include)

file(GLOB purge_system_src "*.cpp")

link_directories(${PROJECT_BINARY_DIR}/../../lib)

add_executable(${PROJECT_NAME} ${purge_system_src} ${common_src})
target_link_libraries(${PROJECT_NAME} ${Boost_LIBRARIES})
target_link_libraries(${PROJECT_NAME} ${CMAKE_THREAD_LIBS_INIT})
target_link_libraries(${PROJECT_NAME} ${COMMON_LIB})
target_link_libraries(${PROJECT_NAME} ${PLUGINS_COMMON_LIB})


install(TARGETS purge_system RUNTIME DESTINATION fledge/tasks)

if(MSYS) #TODO: Is MSYS true when MSVC is true?
    target_link_libraries(purge_system ws2_32 wsock32)
    if(OPENSSL_FOUND)
        target_link_libraries(purge_system ws2_32 wsock32)
    endif()
endif()
