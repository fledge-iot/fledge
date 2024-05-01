cmake_minimum_required (VERSION 2.8.8)
project (South)


set(CMAKE_CXX_FLAGS_DEBUG "-O0 -ggdb -DPy_DEBUG")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11 -Wall -Wextra -Wsign-conversion")
set(CMAKE_CXX_FLAGS_PROFILING "-O2 -pg")
set(DLLIB -ldl)
set(UUIDLIB -luuid)
set(COMMON_LIB common-lib)
set(SERVICE_COMMON_LIB services-common-lib)
set(EXEC fledge.services.south)

include_directories(. include ../../thirdparty/Simple-Web-Server ../../thirdparty/rapidjson/include  ../common/include ../../common/include)

find_package(Threads REQUIRED)

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

if(APPLE)
    set(OPENSSL_ROOT_DIR "/usr/local/opt/openssl")
endif()

# Find python3.x dev/lib package
find_package(PkgConfig REQUIRED)
if(${CMAKE_VERSION} VERSION_LESS "3.12.0")
    pkg_check_modules(PYTHON REQUIRED python3)
else()
    if("${OS_NAME}" STREQUAL "mendel")
        # We will explicitly set include path later for NumPy.
        find_package(Python3 REQUIRED COMPONENTS Interpreter Development )
    else()
        find_package(Python3 REQUIRED COMPONENTS Interpreter Development NumPy)
    endif()
endif()

file(GLOB south_src "*.cpp")

# Add Python 3.x header files
if(${CMAKE_VERSION} VERSION_LESS "3.12.0")
    include_directories(${PYTHON_INCLUDE_DIRS})
else()
    if("${OS_NAME}" STREQUAL "mendel")
        # The following command gets the location of NumPy.
        execute_process(
            COMMAND python3
                -c "import numpy; print(numpy.get_include())"
                OUTPUT_VARIABLE Python3_NUMPY_INCLUDE_DIRS
                OUTPUT_STRIP_TRAILING_WHITESPACE
        )
        # Now we can add include directories as usual.
        include_directories(${Python3_INCLUDE_DIRS} ${Python3_NUMPY_INCLUDE_DIRS})
    else()
        include_directories(${Python3_INCLUDE_DIRS} ${Python3_NUMPY_INCLUDE_DIRS})
    endif()
endif()

link_directories(${PROJECT_BINARY_DIR}/../../lib)

add_executable(${EXEC} ${south_src} ${common_src} ${services_src})
target_link_libraries(${EXEC} ${Boost_LIBRARIES})
target_link_libraries(${EXEC} ${CMAKE_THREAD_LIBS_INIT})
target_link_libraries(${EXEC} ${DLLIB})
target_link_libraries(${EXEC} ${UUIDLIB})
target_link_libraries(${EXEC} ${COMMON_LIB})
target_link_libraries(${EXEC} ${SERVICE_COMMON_LIB})

install(TARGETS ${EXEC} RUNTIME DESTINATION fledge/services)

if(MSYS) #TODO: Is MSYS true when MSVC is true?
    target_link_libraries(${EXEC} ws2_32 wsock32)
    if(OPENSSL_FOUND)
        target_link_libraries(${EXEC} ws2_32 wsock32)
    endif()
endif()

# Set profiling flags if 'Profiling' build
if(CMAKE_BUILD_TYPE STREQUAL "Profiling")
    message("Building in Profiling mode")
    set_target_properties(${EXEC} PROPERTIES COMPILE_FLAGS "${CMAKE_CXX_FLAGS_PROFILING}")
    # define 'PROFILING' flag used by service to change directory
    target_compile_definitions(${EXEC} PRIVATE PROFILING=1)
    set(CMAKE_SHARED_LINKED_FLAGS "${CMAKE_SHARED_LINKED_FLAGS} -O2 -pg")
    target_link_libraries(${EXEC} -O2 -pg)
endif()

