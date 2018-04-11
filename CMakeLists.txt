cmake_minimum_required (VERSION 2.8.8)
project (FogLAMP)

set(CMAKE_CXX_FLAGS "-std=c++11 -O3")

add_subdirectory(C/services/storage)
add_subdirectory(C/plugins/storage/postgres)
add_subdirectory(C/plugins/storage/sqlite)
add_subdirectory(C/services/south)
add_subdirectory(C/plugins/south/dummy)

