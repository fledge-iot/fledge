cmake_minimum_required(VERSION 2.6.0)

project(PI_Server_V2)

set(CMAKE_CXX_FLAGS "-std=c++11 -O3")
# Add here all needed FogLAMP libraries as list
set(NEEDED_FOGLAMP_LIBS common-lib plugins-common-lib)

set(COMMON_LIBS -lssl -lcrypto)

# Find source files
file(GLOB SOURCES *.cpp)

# Include header files
include_directories(include)
include_directories(../../../services/common/include)
include_directories(../../../common/include)
include_directories(../../../plugins/common/include)
include_directories(../../../thirdparty/Simple-Web-Server)
include_directories(../../../thirdparty/rapidjson/include)
link_directories(${PROJECT_BINARY_DIR}/../../../lib)

# Create shared library
add_library(${PROJECT_NAME} SHARED ${SOURCES})
target_link_libraries(${PROJECT_NAME} ${NEEDED_FOGLAMP_LIBS})
target_link_libraries(${PROJECT_NAME} ${COMMON_LIBS})
set_target_properties(${PROJECT_NAME} PROPERTIES SOVERSION 1)

# Install library
install(TARGETS ${PROJECT_NAME} DESTINATION foglamp/plugins/north/${PROJECT_NAME})
