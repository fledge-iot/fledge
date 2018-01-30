.. Developers' Guide

.. |br| raw:: html

   <br />

.. Images


.. Links

.. Links in new tabs

.. |unit test| raw:: html

   <a href="https://en.wikipedia.org/wiki/Unit_testing" target="_blank">here</a>

.. |integration test| raw:: html

   <a href="https://en.wikipedia.org/wiki/Integration_testing" target="_blank">here</a>

.. |system test| raw:: html

   <a href="https://en.wikipedia.org/wiki/System_testing" target="_blank">here</a>


.. =============================================


******************************
System Test Utility and Suites
******************************

FogLAMP comes with a test utility that facilitates the work of developers who wish to implement new plugins or modify the core of the platform. The utility is extremely simple yet powerful: it relies on a set of scripts that allow the full automation of the tests.


First, Some Terminology
=======================

Before we start our adventure in the world of FogLAMP testing, let's set a common background. These are some terms that are used by the FogLAMP developers and you will find in this documentation:

- **Unit tests**: these are tests that developers prepare to test their functions and modules. Unit tests can vary in complexity, but in principle they are meant to test a small piece of code. A unit test does not have a particular meaning to users, but it is an essential part of the software development: by running unit tests, developers can check fo a modified piece of code still behaves as expected and it will not cause issues to the whole system. Unit testing is explained |unit test|.
- **Integration tests**: these are tests that developers prepare to test larger modules or microservices. Integration tests usually require a significant development effort in building other mocked modules and services. We are not planning to provide any integration test in the foreseeable future. Integration testing is explained |integration test|.
- **System tests**: these are tests that can be used by developers and even by power users who want to test the entire system. In order to execute this tests, FogLAMP must be built, installed (although it could be in a development environment) and ready to run. System testing is explained |system test|.
- **Test suite**: this is a set of tests combined together to execute a meaningful test. Example of test suites are a *smoke test* (a quick and simple system test used to verify that FogLAMP is working properly), or *end-to-end test* (a test used to verify that FogLAMP can successfully collect, store and forward data from South to North and East/West or from North to South and East/West.


FogLAMP System Test Principles
==============================


Test Files
----------

Tests rely on a set of test files that can be combined together following the logic of a specific test. Test files are like bricks or building blocks that can be used to create test suites. Test files may, for example, stop and start FogLAMP, inject a set of data points, read data from FogLAMP or send data North. They may be optionally paired with *description files*, used to five a brief description of teh test file, and with *ReStructuredText files*, used to provide a more detailed explanation. Test, description and ReStructuredText files must have the same name. |br| Test files are organized by type, for example bash and Python scripts or executables.


Suite Directories
-----------------

Each test suite is "physically" a directory, and the name of the test suite is the name of the directory. Suites are self-contained, i.e. everything that is defined or executed in a suite is stored in the suite directory, with the only exception of the test files, which are referenced in the *suite files*.


Suite Files
-----------

Suite files are bash scripts that are automatically executed in alphabetical order. They are optionally paired with *description files*, used to give a brief description of the suite file, and with *ReStructuredText files*, used to provide a more detailed explanation. Suite, description and ReStructuredText files must have the same name. |br| Suite files automatically generate an output that is compared with expected results. When the output of a suite file does not match the expected result, the test fails.


foglamp-test
------------
*foglamp-test* is the utility used to execute test suites. The utility is position-dependent, i.e. it must be executed from the directory where it is stored. All the directories at the same level of the utility are identified at test suites and the name if the directory is the name of the suite. In fact, the utility must be executed as ``./foglamp-test <test-suite>``, where *test-suite* is the name of the suite to execute and the name of the suite directory.


Directories and Files
---------------------

This is a list of directories, sub-directories and files that are used in system tests. |br|

The starting point is the **system test base directory**. You will find it in the FogLAMP source repository under *tests/system*.

- Under the system test base directory we have:

  - **suites**: the directory containing the test suites.

    - *foglamp-test*: the system test utility. It must be executed from this position with the command ``./foglamp-test <test-suite>``, where *test-suite* is a sub-directory and the name of the suite that you want to execute.
    - *test-suite*: any sub-directory at this position is a test suite.

      - *suite.desc*: an optional file containing a brief description of the test suite
      - *suite.rst*: an optional ReStructuredText file contaning a more comprehensive description of the test suite
      - **e**: a directory containing all the expected results from the execution of the test suite. Files in this directory have the same name of the suite files and suffix *.expected*.
      - **r**: a directory containing all the results from the execution of a test suite. This directory contains files with the same name of the suite files, with two suffixes:

        - *.result*: files containing standard output and standard error as a result of the execution of the suite files.
        - *.temp*: temporary files generated by the suite files contaning temporary and intermidate information, often used to prepare the result files.

      - **t**: a directory containing the suite files that will be executed in chronological order. This directory contains files with the same name and the following suffixes:

        - *.test*: the bash script suite file.
        - *.desc*: an optional file containing a short description of the suite file.
        - *.rst*: an optional ReStructuredText file containing a more comprehensive description of the suite file.

  - **tests**: the directory containing the test files. Test files are organized in these sub-directories:

    - **bash**: a directory containing test files written in bash. The directory contains files with teh same name and the following suffixes:

      - *.bash*: the test file
      - *.desc*: an optional file containing a short description of the test file.
      - *.rst*: an optional ReStructuredText file containing a more comprehensive description of the test file.

This is an example of a direcory tree from the system test base directory:

.. code-block:: console

  foglamp@vbox-dev:~/FogLAMP/tests/system$ tree
  .
  ├── README.rst
  ├── suites
  │   ├── foglamp-test
  │   └── smoke
  │       ├── e
  │       │   ├── 001_prepare.expected
  │       │   ├── 002_start.expected
  │       │   └── README.rst
  │       ├── r
  │       │   ├── 001_prepare.result
  │       │   ├── 002_start.result
  │       │   ├── 002_start.temp
  │       │   ├── 003_inject.result
  │       │   └── README.rst
  │       ├── suite.desc
  │       └── t
  │           ├── 001_prepare.test
  │           ├── 001_start.desc
  │           ├── 002_start.test
  │           ├── 003_inject.test
  │           └── README.rst
  └── tests
      ├── bash
      │   ├── check_foglamp_status.bash
      │   ├── check_foglamp_status.desc
      │   ├── exec_any_foglamp_command.bash
      │   ├── exec_any_foglamp_command.desc
      │   ├── inject_fogbench_data.bash
      │   └── README.rst
      └── README.rst

  7 directories, 23 files
  foglamp@vbox-dev:~/FogLAMP/tests/system$


How to Prepare a Test Suite
===========================

In this section we will see how to prepare a new test suite. The objective is to familiarize with the various components, so that you may create your own suite. 


Step 1: the Building Blocks, the Test Files
-------------------------------------------

The first thing to do is to create some building blocks. These are test files, normally written in bash, that can be reused as many times as you wish in multiple test suites. |br| There are no limitations in the logic you may want to add to each test file, but you should consider these guidelines:

- **Verify the consistency of each file**: the most common error in the test suite is the modification of a test file that is used in many test suites. When you modify a test file, you must make sure that the file will produce the same results. If the results change, then you must modify all the result files affected by the test file.
- **Document the test file**: it is the most obvious suggestion, but also the one that is often ignored. Try to avoid to create test files that are obscured, with unknown behaviour, because there is a high risk of recreating many times the very same test file simply because you are not aware that there is another test file with the same logic.
- **Do not make test files too generic**: it is ok to pass parameter to test files and make them act as called libraries, but also consider that the more generic the file is, the more it is likely that the execution will produce an unexpected behavior that will cause false failures.
- **Test files are normally executed in the same process of foglamp-test**: although this is not mandatory, it is a norm to execute the file as part of the same bash script, i.e. in the same process and with the same environment. This also means:

  - Do not use ``exit`` commands: the command will close the foglamp-test utility.
  - Do not change the value of environment variables: this may cause issues in the execution of test files that follow, causing unexpected results.
  - Use pre-defined variables whenever possible: foglamp-test provides a set of predifined variable that are the preferred choice to interact with FogLAMP.

These are examples of test files:

- *check_foglamp_status*: this script executes the ``foglamp status`` command, but it only provides the firs line of the command, i.e. if FogLAMP is running or not.
- *start_foglamp*: this script executes the ``foglamp start`` command, but the output is normally ignored.
- *exec_any_foglamp_command*: this is a script used to generically call any command of the *foglamp* utility. 


Pre-defined Variables
~~~~~~~~~~~~~~~~~~~~~

These pre-defined variables are helpful in the test files:

- **FOGLAMP_EXE**: the foglamp script. Based on the *FOGLAMP_ROOT* variable and the presence of the *foglamp* command, the *foglamp-test* utility has already selected the script for you. By using the variable, you will have consistent executions along the whole suite.
- **FOGBENCH_EXE**: the fogbench script. As for *FOGLAMP_EXE*, this variable guarantees the consistency of the execution along the whole suite.


Step 2: the Suite Files
-----------------------

Once you have a set of test files available, you can combine them together in the suite files. There are no limitations in the number of test files added to the suite files, or to the logic added to the suite file to support the execution of the test: theoretically, a developer may completely ignore the test files and add all the logic in the suite file, but in doing so he/she will certainly replicate most of the logic. |br| Here are some guidelines you may want to adopt when you prepare a suite file:

- **Do not use** ``exit``: since the suite files are executed in the same process, the ``exit`` command will cause the *foglamp-test* utility to terminate.
- **Send unnecessary output to /dev/null**: if you do not want to include the output of a command or a test file in the result file, simply add ``> /dev/null 2>&1`` to the line in the suite file.
- **Send intermediate data to a temporary file**: the correct format is to add ``> $RESULT_DIR/$test_name.temp 2>&1`` to the command that you need to review the output before it will become part of the result file.
- **Use** ``echo -e`` **or** ``expect`` **to manage interactive input**: some scripts require interactive input, and commands like ``echo -e`` can help  in automating the input.


Pre-defined Variables
~~~~~~~~~~~~~~~~~~~~~

This is a list of variables that may be helpful when you create a suite file. These variables are available in the test files and in the suite files, and so are *FOGLAMP_EXE* and *FOGBENCH_EXE*.

- **TEST_BASEDIR**: the directory containing the test files.
- **RESULT_DIR**: the directory containing the result and the temporary files.
- **test_name**: the name of the suite file.


Step 3: Putting Everything Together
-----------------------------------

Now you are almost ready to execute your first suite, there is still one important thing missing: the result files. Result files are necessary to provide a comparison and to make sure that the tests are successful (or they fail). Creating result files is easy, just follow these guidelines:

- **Set a relatively safe environment**: you will use this environment to prepare the result files.
- **Execute the foglamp-test utility**: it is likely that the utility will stop at the first test with a failure. This happens if the suite file generates and output (a *.result* file), but there are not expected files (a *.expect* file) to compare.
- **Check and approve the result file**: once you are happy with the content of the result file, simply move the file into the *e* (as in "expected") directory, by changing the suffix to *.expected*.
- **Repeat again until the suite is completed**: when you execute the foglamp-test utility again, the first test will pass, but then the utility will stop on the second test. You must repeat this procedure for all the suite files.

One last point: don't worry about the *.result* and *.temp* files left by the utility: *foglamp-test* will remove these files right before the same suite is executed.


Executing a Test Suite
======================



.. note:: This page is currently under construction. Come back soon to check it again!

