cmake_minimum_required(VERSION 2.6)
 
# Locate GTest
find_package(GTest REQUIRED)
include_directories(${GTEST_INCLUDE_DIRS})
include_directories(../../src/C/foglamp/storage/include)
include_directories(../../src/C/foglamp/common/include)
include_directories(../../src/C/thirdparty/rapidjson/include)

file(GLOB test_sources "../../src/C/foglamp/storage/configuration.cpp")
file(GLOB logger_sources "../../src/C/foglamp/common/logger.cpp")
 
# Link runTests with what we want to test and the GTest and pthread library
add_executable(runTests ${test_sources} ${logger_sources} tests.cpp)
target_link_libraries(runTests ${GTEST_LIBRARIES} pthread)

