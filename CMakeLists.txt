cmake_minimum_required (VERSION 2.8.8)
project (FogLAMP)

set(CMAKE_CXX_FLAGS "-std=c++11 -O3")

add_subdirectory(C/common)
add_subdirectory(C/services/common)
add_subdirectory(C/plugins/common)
add_subdirectory(C/services/storage)
add_subdirectory(C/plugins/storage/common)
add_subdirectory(C/plugins/storage/postgres)
add_subdirectory(C/plugins/storage/sqlite)
add_subdirectory(C/plugins/storage/sqlitememory)
add_subdirectory(C/services/south)
add_subdirectory(C/plugins/south/dummy)
#add_subdirectory(C/plugins/south/dht11)     # TODO: this has dependency on libwiringPi C library, which cannot be installed automatically presently in build process, so commenting out dht11 plugin build step for now.
add_subdirectory(C/tasks/north)
add_subdirectory(C/plugins/north/omf)
add_subdirectory(C/plugins/utils)
