cmake_minimum_required (VERSION 2.8.8)
project (Fledge)

set(CMAKE_CXX_FLAGS "-std=c++11 -O3")

find_package(PkgConfig REQUIRED)

add_subdirectory(C/common)
add_subdirectory(C/services/common)
add_subdirectory(C/plugins/common)
add_subdirectory(C/plugins/filter/common)
add_subdirectory(C/services/storage)
add_subdirectory(C/plugins/storage/common)
add_subdirectory(C/plugins/storage/postgres)
add_subdirectory(C/plugins/storage/sqlite)
add_subdirectory(C/plugins/storage/sqlitememory)
add_subdirectory(C/services/south)
add_subdirectory(C/services/south-plugin-interfaces/python)
add_subdirectory(C/services/south-plugin-interfaces/python/async_ingest_pymodule)
add_subdirectory(C/services/notification-plugin-interfaces/python)
add_subdirectory(C/services/filter-plugin-interfaces/python)
add_subdirectory(C/services/filter-plugin-interfaces/python/filter_ingest_pymodule)
add_subdirectory(C/tasks/north)
add_subdirectory(C/plugins/utils)
add_subdirectory(C/plugins/north/PI_Server_V2)
add_subdirectory(C/plugins/north/ocs_V2)

#// FIXME:
set(CMAKE_BUILD_TYPE Debug)
