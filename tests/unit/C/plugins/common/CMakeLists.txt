cmake_minimum_required(VERSION 2.6)

set(CMAKE_CXX_FLAGS "-std=c++11 -O3")
set(UUIDLIB -luuid)
set(COMMONLIB -ldl)
set(LIBCURL_LIB -lcurl)

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

include_directories(../../../../../C/common/include)
include_directories(../../../../../C/plugins/common/include)
include_directories(../../../../../C/services/common/include)
include_directories(../../../../../C/thirdparty/rapidjson/include)
include_directories(../../../../../C/thirdparty/Simple-Web-Server)

set(COMMON_LIB common-lib)
set(SERVICE_COMMON_LIB services-common-lib)
set(PLUGINS_COMMON_LIB plugins-common-lib)

file(GLOB unittests "*.cpp")
 
# Find python3.x dev/lib package
find_package(PkgConfig REQUIRED)
pkg_check_modules(PYTHON REQUIRED python3)

# Add Python 3.x header files
include_directories(${PYTHON_INCLUDE_DIRS})

link_directories(${PYTHON_LIBRARY_DIRS})

link_directories(${PROJECT_BINARY_DIR}/../../../lib)

# Link runTests with what we want to test and the GTest and pthread library
add_executable(RunTests ${unittests})
target_link_libraries(RunTests ${GTEST_LIBRARIES} pthread)
target_link_libraries(RunTests ${Boost_LIBRARIES})
target_link_libraries(RunTests ${UUIDLIB})
target_link_libraries(RunTests ${COMMONLIB})
target_link_libraries(RunTests -lssl -lcrypto -lz)
target_link_libraries(RunTests ${COMMON_LIB})
target_link_libraries(RunTests ${SERVICE_COMMON_LIB})
target_link_libraries(RunTests ${PLUGINS_COMMON_LIB})
target_link_libraries(RunTests ${LIBCURL_LIB})

# Add Python 3.x library
target_link_libraries(RunTests ${PYTHON_LIBRARIES})

