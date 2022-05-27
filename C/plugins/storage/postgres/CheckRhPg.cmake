# Evaluates if rh-postgresql13 is available and enabled and identifies its path

execute_process(
        COMMAND  "scl" "enable" "rh-postgresql13" "command -v pg_isready"
        RESULT_VARIABLE CMD_ERROR
        OUTPUT_VARIABLE CMD_OUTPUT
)

if(${CMD_ERROR} EQUAL 0)
    string(REGEX REPLACE "/bin/pg_isready[\n]" "" RH_POSTGRES_PATH ${CMD_OUTPUT})

    set(RH_POSTGRES_FOUND 1)
    set(RH_POSTGRES_INCLUDE "${RH_POSTGRES_PATH}/include")
    set(RH_POSTGRES_LIB64   "${RH_POSTGRES_PATH}/lib64")
else()
    set(RH_POSTGRES_FOUND 0)
endif()

if(${RH_POSTGRES_FOUND} EQUAL 1)

    MESSAGE( STATUS "INFO: rh-postgresql13 found in the path :${RH_POSTGRES_PATH}:")
else()
    MESSAGE( STATUS "INFO: rh-postgresql13 not found")
endif()
