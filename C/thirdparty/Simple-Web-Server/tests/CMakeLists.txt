if(NOT MSVC)
    add_compile_options(-fno-access-control)
    if (CMAKE_CXX_COMPILER_ID MATCHES "Clang")
        add_compile_options(-Wno-thread-safety)
    endif()
    
    add_executable(io_test io_test.cpp)
    target_link_libraries(io_test simple-web-server)
    add_test(NAME io_test COMMAND io_test)

    add_executable(parse_test parse_test.cpp)
    target_link_libraries(parse_test simple-web-server)
    add_test(NAME parse_test COMMAND parse_test)
endif()

if(OPENSSL_FOUND)
    add_executable(crypto_test crypto_test.cpp)
    target_link_libraries(crypto_test simple-web-server)
    add_test(NAME crypto_test COMMAND crypto_test)
endif()

add_executable(status_code_test status_code_test.cpp)
target_link_libraries(status_code_test simple-web-server)
add_test(NAME status_code_test COMMAND status_code_test)
