cmake_minimum_required(VERSION 2.6)

set(CMAKE_MODULE_PATH ${CMAKE_MODULE_PATH} ${CMAKE_CURRENT_SOURCE_DIR}/../../..)
set(GCOVR_PATH "$ENV{HOME}/.local/bin/gcovr")

# Project configuration
project(RunTests)

include(CodeCoverage)
append_coverage_compiler_flags()

set(CMAKE_CXX_FLAGS "-std=c++11 -O0 -ggdb")
 

# Locate GTest
find_package(GTest REQUIRED)
include_directories(${GTEST_INCLUDE_DIRS})
include_directories(../../../../../../C/services/storage/include)
include_directories(../../../../../../C/services/common/include)
include_directories(../../../../../../C/common/include)
include_directories(../../../../../../C/thirdparty/rapidjson/include)

file(GLOB test_sources "../../../../../../C/services/storage/configuration.cpp")
file(GLOB logger_sources "../../../../../../C/common/logger.cpp")
file(GLOB config_sources "../../../../../../C/common/config_category.cpp")
file(GLOB utils_sources "../../../../../../C/common/json_utils.cpp")
 
# Link runTests with what we want to test and the GTest and pthread library
add_executable(RunTests ${test_sources} ${logger_sources} ${config_sources} ${utils_sources} tests.cpp)
target_link_libraries(RunTests ${GTEST_LIBRARIES} pthread)

setup_target_for_coverage_gcovr_html(
            NAME CoverageHtml
            EXECUTABLE ${PROJECT_NAME}
            DEPENDENCIES ${PROJECT_NAME}
    )

