# This CMake file locates the Fledge header files and libraries
#
# The following variables are set:
# FLEDGE_INCLUDE_DIRS - Path(s) to Fledge headers files found
# FLEDGE_LIB_DIRS - Path to Fledge shared libraries
# FLEDGE_SUCCESS - Set on succes
#
# In case of error use SEND_ERROR and return()
#

# Set defaults paths of installed Fledge SDK package
set(FLEDGE_DEFAULT_INCLUDE_DIR "/usr/include/fledge" CACHE INTERNAL "")
set(FLEDGE_DEFAULT_LIB_DIR "/usr/lib/fledge" CACHE INTERNAL "")

# CMakeLists.txt options
set(FLEDGE_SRC "" CACHE INTERNAL "")
set(FLEDGE_INCLUDE "" CACHE INTERNAL "")
set(FLEDGE_LIB "" CACHE INTERNAL "")

# Return variables
set(FLEDGE_INCLUDE_DIRS "" CACHE INTERNAL "")
set(FLEDGE_LIB_DIRS "" CACHE INTERNAL "")
set(FLEDGE_FOUND "" CACHE INTERNAL "")

# No options set
# If FLEDGE_ROOT env var is set, use it
if (NOT FLEDGE_SRC AND NOT FLEDGE_INCLUDE AND NOT FLEDGE_LIB)
	if (DEFINED ENV{FLEDGE_ROOT})
		message(STATUS "No options set.\n" 
			"   +Using found FLEDGE_ROOT $ENV{FLEDGE_ROOT}")
		set(FLEDGE_SRC $ENV{FLEDGE_ROOT})
	endif()
endif()

# -DFLEDGE_SRC=/some_path or FLEDGE_ROOT path
# Set return variable FLEDGE_INCLUDE_DIRS
if (FLEDGE_SRC)
	unset(_INCLUDE_LIST CACHE)
	file(GLOB_RECURSE _INCLUDE_COMMON "${FLEDGE_SRC}/C/common/*.h")
	file(GLOB_RECURSE _INCLUDE_SERVICES "${FLEDGE_SRC}/C/services/common/*.h")
	file(GLOB_RECURSE _INCLUDE_PLUGINS_FILTER_COMMON "${FLEDGE_SRC}/C/plugins/filter/common/*.h")
	list(APPEND _INCLUDE_LIST ${_INCLUDE_COMMON} ${_INCLUDE_SERVICES})
	foreach(_ITEM ${_INCLUDE_LIST})
		get_filename_component(_ITEM_PATH ${_ITEM} DIRECTORY)
		list(APPEND FLEDGE_INCLUDE_DIRS ${_ITEM_PATH})
	endforeach()
	list(APPEND FLEDGE_INCLUDE_DIRS "${FLEDGE_SRC}/C/thirdparty/rapidjson/include")
	unset(INCLUDE_LIST CACHE)

	list(REMOVE_DUPLICATES FLEDGE_INCLUDE_DIRS)

	string (REPLACE ";" "\n   +" DISPLAY_PATHS "${FLEDGE_INCLUDE_DIRS}")
	if (NOT DEFINED ENV{FLEDGE_ROOT})
		message(STATUS "Using -DFLEDGE_SRC option for includes\n   +" "${DISPLAY_PATHS}")
	else()
		message(STATUS "Using FLEDGE_ROOT for includes\n   +" "${DISPLAY_PATHS}")
	endif()

	if (NOT FLEDGE_INCLUDE_DIRS)
		message(SEND_ERROR "Needed Fledge header files not found in path ${FLEDGE_SRC}/C")
		return()
	endif()
else()
	# -DFLEDGE_INCLUDE=/some_path
	if (NOT FLEDGE_INCLUDE)
		set(FLEDGE_INCLUDE ${FLEDGE_DEFAULT_INCLUDE_DIR})
		message(STATUS "Using Fledge dev package includes " ${FLEDGE_INCLUDE})
	else()
		message(STATUS "Using -DFLEDGE_INCLUDE option " ${FLEDGE_INCLUDE})
	endif()
	# Remove current value from cache
	unset(_FIND_INCLUDES CACHE)
	# Get up to date var from find_path
	find_path(_FIND_INCLUDES NAMES plugin_api.h PATHS ${FLEDGE_INCLUDE})
	if (_FIND_INCLUDES)
		list(APPEND FLEDGE_INCLUDE_DIRS ${_FIND_INCLUDES})
	endif()
	# Remove current value from cache
	unset(_FIND_INCLUDES CACHE)

	if (NOT FLEDGE_INCLUDE_DIRS)
		message(SEND_ERROR "Needed Fledge header files not found in path ${FLEDGE_INCLUDE}")
		return()
	endif()
endif()

#
# Fledge Libraries
#
# Check -DFLEDGE_LIB=/some path is valid
# or use FLEDGE_SRC/cmake_build/C/lib
# FLEDGE_SRC might have been set to FLEDGE_ROOT above
#
if (FLEDGE_SRC)
	# Set return variable FLEDGE_LIB_DIRS
        set(FLEDGE_LIB "${FLEDGE_SRC}/cmake_build/C/lib")

	if (NOT DEFINED ENV{FLEDGE_ROOT})
		message(STATUS "Using -DFLEDGE_SRC option for libs \n   +" "${FLEDGE_SRC}/cmake_build/C/lib")
	else()
		message(STATUS "Using FLEDGE_ROOT for libs \n   +" "${FLEDGE_SRC}/cmake_build/C/lib")
	endif()

	if (NOT EXISTS "${FLEDGE_SRC}/cmake_build")
		message(SEND_ERROR "Fledge has not been built yet in ${FLEDGE_SRC}  Compile it first.")
		return()
	endif()

	# Set return variable FLEDGE_LIB_DIRS
	set(FLEDGE_LIB_DIRS "${FLEDGE_SRC}/cmake_build/C/lib")
else()
	if (NOT FLEDGE_LIB)
		set(FLEDGE_LIB ${FLEDGE_DEFAULT_LIB_DIR})
		message(STATUS "Using Fledge dev package libs " ${FLEDGE_LIB})
	else()
		message(STATUS "Using -DFLEDGE_LIB option " ${FLEDGE_LIB})
	endif()
	# Set return variable FLEDGE_LIB_DIRS
	set(FLEDGE_LIB_DIRS ${FLEDGE_LIB})
endif()

# Check NEEDED_FLEDGE_LIBS in libraries in FLEDGE_LIB_DIRS
# NEEDED_FLEDGE_LIBS variables comes from CMakeLists.txt
foreach(_LIB ${NEEDED_FLEDGE_LIBS})
	# Remove current value from cache
	unset(_FOUND_LIB CACHE)
	# Get up to date var from find_library
	find_library(_FOUND_LIB NAME ${_LIB} PATHS ${FLEDGE_LIB_DIRS})
	if (_FOUND_LIB)
		# Extract path form founf library file
		get_filename_component(_DIR_LIB ${_FOUND_LIB} DIRECTORY)
	else()
		message(SEND_ERROR "Needed Fledge library ${_LIB} not found in ${FLEDGE_LIB_DIRS}")
		return()
	endif()
	# Remove current value from cache
	unset(_FOUND_LIB CACHE)
endforeach()

# Set return variable FLEDGE_FOUND
set(FLEDGE_FOUND "true")
