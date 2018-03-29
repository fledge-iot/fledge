cmake_minimum_required(VERSION 2.6)

set(CMAKE_CXX_FLAGS "-std=c++11 -O3")
 
# Locate GTest
find_package(GTest REQUIRED)
include_directories(${GTEST_INCLUDE_DIRS})
include_directories(../../../../../../C/services/storage/include)
include_directories(../../../../../../C/services/common/include)
include_directories(../../../../../../C/thirdparty/rapidjson/include)

file(GLOB test_sources "../../../../../../C/services/storage/configuration.cpp")
file(GLOB logger_sources "../../../../../../C/services/common/logger.cpp")
 
# Link runTests with what we want to test and the GTest and pthread library
add_executable(runTests ${test_sources} ${logger_sources} tests.cpp)
target_link_libraries(runTests ${GTEST_LIBRARIES} pthread)

