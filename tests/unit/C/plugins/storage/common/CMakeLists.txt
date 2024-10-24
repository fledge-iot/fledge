cmake_minimum_required(VERSION 2.6)

set(CMAKE_MODULE_PATH ${CMAKE_MODULE_PATH} ${CMAKE_CURRENT_SOURCE_DIR}/../../..)
set(GCOVR_PATH "$ENV{HOME}/.local/bin/gcovr")

# Project configuration
project(RunTests)

# Fledge libraries
set(COMMON_LIB              common-lib)
set(SERVICE_COMMON_LIB      services-common-lib)
set(PLUGINS_COMMON_LIB      plugins-common-lib)

set(CMAKE_CXX_FLAGS "-std=c++11 -O0")

include(CodeCoverage)
append_coverage_compiler_flags()

# Locate GTest
find_package(GTest REQUIRED)
include_directories(${GTEST_INCLUDE_DIRS})
include_directories(../../../../../../C/plugins/storage/common/include)
include_directories(../../../../../../C/common/include)

# Exe creation
link_directories(
        ${PROJECT_BINARY_DIR}/../../../../lib
)


# Find python3.x dev/lib package
find_package(PkgConfig REQUIRED)
if(${CMAKE_VERSION} VERSION_LESS "3.12.0")
    pkg_check_modules(PYTHON REQUIRED python3)
else()
    find_package(Python3 COMPONENTS Interpreter Development)
endif()

if(${CMAKE_VERSION} VERSION_LESS "3.12.0")
    link_directories(${PYTHON_LIBRARY_DIRS})
else()
    link_directories(${Python3_LIBRARY_DIRS})
endif()

file(GLOB test_sources "../../../../../../C/plugins/storage/common/*.cpp")

 
# Link runTests with what we want to test and the GTest and pthread library
add_executable(RunTests ${test_sources} tests.cpp)

#setting BOOST_COMPONENTS to use pthread library only
set(BOOST_COMPONENTS thread)
find_package(Boost 1.53.0 COMPONENTS ${BOOST_COMPONENTS} REQUIRED)
target_link_libraries(RunTests ${COMMON_LIB})
target_link_libraries(RunTests ${SERVICE_COMMON_LIB})
target_link_libraries(RunTests ${PLUGINS_COMMON_LIB})
target_link_libraries(RunTests ${GTEST_LIBRARIES} pthread ${COMMONLIB} )

# Add Python 3.x library
if(${CMAKE_VERSION} VERSION_LESS "3.12.0")
        target_link_libraries(${PROJECT_NAME} ${PYTHON_LIBRARIES})
else()
        target_link_libraries(${PROJECT_NAME} ${Python3_LIBRARIES})
endif()

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
