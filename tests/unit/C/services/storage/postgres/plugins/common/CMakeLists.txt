cmake_minimum_required(VERSION 2.6)

set(CMAKE_MODULE_PATH ${CMAKE_MODULE_PATH} ${CMAKE_CURRENT_SOURCE_DIR}/../../../../..)
set(GCOVR_PATH "$ENV{HOME}/.local/bin/gcovr")

# Project configuration
project(RunTests)

set(CMAKE_CXX_FLAGS "-std=c++11 -O0")
 
include(CodeCoverage)
append_coverage_compiler_flags()

# Locate GTest
find_package(GTest REQUIRED)
include_directories(${GTEST_INCLUDE_DIRS})
include_directories(../../../../../../../../C/plugins/storage/common/include)
include_directories(../../../../../../../../C/common/include)

file(GLOB test_sources "../../../../../../../../C/plugins/storage/common/*.cpp")
set(common_sources "../../../../../../../../C/common/string_utils.cpp")

 
# Link runTests with what we want to test and the GTest and pthread library
add_executable(RunTests ${test_sources} ${common_sources} tests.cpp)
#setting BOOST_COMPONENTS to use pthread library only
set(BOOST_COMPONENTS thread)
find_package(Boost 1.53.0 COMPONENTS ${BOOST_COMPONENTS} REQUIRED)
target_link_libraries(RunTests ${GTEST_LIBRARIES} pthread)

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

