cmake_minimum_required(VERSION 2.6)

set(CMAKE_CXX_FLAGS "-std=c++11 -O3")
set(UUIDLIB -luuid)
 
# Locate GTest
find_package(GTest REQUIRED)
include_directories(${GTEST_INCLUDE_DIRS})

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

include_directories(../../../../C/common/include)
include_directories(../../../../C/services/common/include)
include_directories(../../../../C/thirdparty/rapidjson/include)
include_directories(../../../../C/thirdparty/Simple-Web-Server)

file(GLOB test_sources "../../../../C/common/*.cpp")
file(GLOB logger_sources "../../../../C/services/common/logger.cpp")
 
# Link runTests with what we want to test and the GTest and pthread library
add_executable(test_query ${test_sources} ${logger_sources} test_query.cpp)
target_link_libraries(test_query ${GTEST_LIBRARIES} pthread)
target_link_libraries(test_query  ${Boost_LIBRARIES})
target_link_libraries(test_query  ${UUIDLIB})
add_executable(test_resultset ${test_sources} ${logger_sources} test_resultset.cpp)
target_link_libraries(test_resultset ${GTEST_LIBRARIES} pthread)
target_link_libraries(test_resultset  ${Boost_LIBRARIES})
target_link_libraries(test_resultset  ${UUIDLIB})
add_executable(test_reading ${test_sources} ${logger_sources} test_reading.cpp)
target_link_libraries(test_reading ${GTEST_LIBRARIES} pthread)
target_link_libraries(test_reading  ${Boost_LIBRARIES})
target_link_libraries(test_reading  ${UUIDLIB})

