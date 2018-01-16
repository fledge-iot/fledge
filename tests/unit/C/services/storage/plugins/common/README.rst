*************************************************
Unit Test for Common Components of Storage Plugin
*************************************************

Require Google Unit Test framework

Install with:
::
    sudo apt-get install libgtest-dev
    cd /usr/src/gtest
    cmake CMakeLists.txt
    sudo make
    sudo make install

To build the unit test:
::
    mkdir build
    cd build
    cmake ..
    make
    ./runTests

