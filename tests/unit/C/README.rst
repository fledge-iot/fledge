*********************
C/C++ Code Unit Tests
*********************

This directory tree contains the unit tests for the C and C++ code.

Prequisite
==========

These tests are written using the Google Test framework. This should be installed on your machine

To install Google Test, you can use the following commands:

- sudo ./requirement.sh

Running Tests
=============

To run all the unit tests go to the directory scripts and execute the script

- RunAllTests

This will run all unit tests and place the JUnit XML files in the directory results

To generate coverage reports, go to the directory scripts and execute the script as follows:

- RunAllTests coverageHtml

This will run all unit tests and report test coverage results in 'build/CoverageHtml/index.html' file w.r.t. path of CMakeLists.txt files.

- RunAllTests coverageXml

This will run all unit tests and report test coverage results in 'build/CoverageXml.xml' file w.r.t. path of CMakeLists.txt files.

