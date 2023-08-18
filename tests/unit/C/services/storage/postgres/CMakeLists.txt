cmake_minimum_required(VERSION 2.6)

set(CMAKE_MODULE_PATH ${CMAKE_MODULE_PATH} ${CMAKE_CURRENT_SOURCE_DIR}/../../..)
set(GCOVR_PATH "$ENV{HOME}/.local/bin/gcovr")

# Project configuration
project(RunTests)

set(CMAKE_CXX_FLAGS "-std=c++11 -O0")

set(COMMON_LIB common-lib)

include(CodeCoverage)
append_coverage_compiler_flags()

# Locate GTest
find_package(GTest REQUIRED)
include_directories(${GTEST_INCLUDE_DIRS})
include_directories(../../../../../../C/services/storage/include)
include_directories(../../../../../../C/services/common/include)
include_directories(../../../../../../C/common/include)
include_directories(../../../../../../C/thirdparty/rapidjson/include)

file(GLOB test_sources "../../../../../../C/services/storage/configuration.cpp")
 
# Link runTests with what we want to test and the GTest and pthread library
add_executable(RunTests ${test_sources} ${logger_sources} ${config_sources} ${utils_sources} tests.cpp)
#setting BOOST_COMPONENTS to use pthread library only
set(BOOST_COMPONENTS thread)
find_package(Boost 1.53.0 COMPONENTS ${BOOST_COMPONENTS} REQUIRED)
target_link_libraries(RunTests ${GTEST_LIBRARIES} pthread)

link_directories(${PROJECT_BINARY_DIR}/../../../../lib)
target_link_libraries(RunTests ${COMMON_LIB})

setup_target_for_coverage_gcovr_html(
            NAME CoverageHtml
            EXECUTABLE ${PROJECT_NAME}
            DEPENDENCIES ${PROJECT_NAME}
    )

setup_target_for_coverage_gcovr_xml(
            NAME CoverageXml
            EXECUTABLE ${PROJECT_NAME}
            DEPENDENCIES ${PROJECT_NAME}
    )

