cmake_minimum_required (VERSION 2.8.8)
project (statistics_history)

set(CMAKE_CXX_FLAGS_DEBUG "-O0 -ggdb")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11 -Wall -Wextra -Wsign-conversion")
set(UUIDLIB -luuid)
set(COMMON_LIB -lcommon-lib)

include_directories(. include ../../thirdparty/Simple-Web-Server ../../thirdparty/rapidjson/include  ../../common/include)

find_package(Threads REQUIRED)

set(BOOST_COMPONENTS system thread)

find_package(Boost 1.53.0 COMPONENTS ${BOOST_COMPONENTS} REQUIRED)
include_directories(SYSTEM ${Boost_INCLUDE_DIR})

file(GLOB statistics_history_src "*.cpp")

link_directories(${PROJECT_BINARY_DIR}/../../lib)

add_executable(statistics_history ${statistics_history_src} ${common_src})
target_link_libraries(statistics_history ${Boost_LIBRARIES})
target_link_libraries(statistics_history ${CMAKE_THREAD_LIBS_INIT})
target_link_libraries(statistics_history ${UUIDLIB})
target_link_libraries(${PROJECT_NAME} ${COMMON_LIB})


install(TARGETS statistics_history RUNTIME DESTINATION foglamp/tasks)

if(MSYS) #TODO: Is MSYS true when MSVC is true?
    target_link_libraries(statistics_history ws2_32 wsock32)
    if(OPENSSL_FOUND)
        target_link_libraries(statistics_history ws2_32 wsock32)
    endif()
endif()
