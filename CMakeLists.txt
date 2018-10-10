cmake_minimum_required (version 2.8.8)
project (foglamp)

set(cmake_cxx_flags "-std=c++11 -o3")

add_subdirectory(c/common)
add_subdirectory(c/services/common)
add_subdirectory(c/plugins/common)
add_subdirectory(c/plugins/filter/common)
add_subdirectory(c/services/storage)
add_subdirectory(c/plugins/storage/common)
add_subdirectory(c/plugins/storage/postgres)
add_subdirectory(c/plugins/storage/sqlite)
add_subdirectory(c/plugins/storage/sqlitememory)
add_subdirectory(c/services/south)
add_subdirectory(c/tasks/north)
add_subdirectory(c/plugins/utils)

# fixme
set(cmake_build_type debug)
