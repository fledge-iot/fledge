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

FogLAMP comes with a test utility that facilitates the work of developers who wish to implement new plugins or modify the core of the platform. The utility is simple yet powerful: it relies on a set of scripts that allow the full automation of the tests.


First, Some Terminology
=======================

Before we start our adventure in the world of FogLAMP testing, let's set a common background. These are some terms that are used by the FogLAMP developers that you will find in this documentation:

- **Unit tests**: these are tests that developers prepare to test their functions and modules. Unit tests can vary in complexity, but in principle they are meant to test a small piece of code. A unit test does not have a particular meaning to users, but it is an essential part of the software development: by running unit tests, developers can check if a modified piece of code still behaves as expected and it will not cause issues to the whole system. Unit testing is explained |unit test|.
- **Integration tests**: these are tests that developers prepare to test larger modules or microservices. Integration tests usually require a significant development effort in building other mocked modules and services. We are not planning to provide any integration test in the foreseeable future. Integration testing is explained |integration test|.
- **System tests**: these are tests that can be used by developers and even by power users who want to test FogLAMP running with all the necessary microservices running. In order to execute these tests, FogLAMP must be built, installed (although it could be in a development environment) and ready to run. System testing is explained |system test|.
- **Test suite**: this is a set of tests combined together to execute a meaningful test of the system. Examples of test suites are a *smoke test* (a quick and simple system test used to verify that FogLAMP is working properly), or *end-to-end test* (a test used to verify that FogLAMP can successfully collect, store and forward data from South to North and East/West or from North to South and East/West.
- **End to end tests**: this is a type of system test that, in FogLAMP terms, can test the collection, storage and transfer of data. For example, we can call "End to End" test a suite that tests the collection of data from a South plugin and the storage of the same data in a PI server, through the North plugin. The concept of "End to End" relies on the fact that data is collected from one end (the South plugin) and it is tested all the way up to the other end (the PI Server).


FogLAMP System Test Principles
==============================


Test Files
----------

Tests rely on a set of test files that can be combined together following the logic of a specific test. Test files are like bricks or building blocks that can be used to create test suites. Test files may, for example, stop and start FogLAMP, inject a set of data points, read data from FogLAMP or send data North. They may be optionally paired with *description files* to provide a brief description of the test file, and with *ReStructuredText files*, to provide a more detailed explanation. Test, description and ReStructuredText files must have the same name. |br| Test files are organized by type, for example bash and Python scripts or executables.


Suite Directories
-----------------

Each test suite is "physically" a directory, and the name of the test suite is the name of the directory. Suites are self-contained, i.e. everything that is defined or executed in a suite is stored in the suite directory, with the only exception of the test files, which are referenced in the *suite files*.


Suite Files
-----------

Suite files are bash scripts that are automatically executed in alphabetical order. They are optionally paired with *description files*, to provide a brief description of the suite file, and with *ReStructuredText files*, to provide a more detailed explanation. Suite, description and ReStructuredText files must have the same name. |br| Suite files automatically generate an output that is compared with expected results. When the output of a suite file does not match the expected result, the test fails.


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

      - *suite.desc*: an optional file containing a brief description of the test suite.
      - *suite.rst*: an optional ReStructuredText file contaning a more comprehensive description of the test suite.
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
  │       │   ├── 003_inject.expected
  │       │   ├── 004_wait_for_flush.expected
  │       │   ├── 005_read_from_REST.expected
  │       │   └── README.rst
  │       ├── r
  │       │   ├── 001_prepare.result
  │       │   ├── 002_start.result
  │       │   ├── 002_start.temp
  │       │   ├── 003_inject.1.temp
  │       │   ├── 003_inject.2.temp
  │       │   ├── 003_inject.result
  │       │   ├── 004_wait_for_flush.result
  │       │   ├── 005_read_from_REST.result
  │       │   ├── 005_read_from_REST.temp
  │       │   └── README.rst
  │       ├── suite.desc
  │       └── t
  │           ├── 001_prepare.test
  │           ├── 001_start.desc
  │           ├── 002_start.test
  │           ├── 003_inject.test
  │           ├── 004_wait_for_flush.test
  │           ├── 005_read_from_REST.test
  │           └── README.rst
  └── tests
      ├── bash
      │   ├── check_foglamp_status.bash
      │   ├── check_foglamp_status.desc
      │   ├── count_assets_http.bash
      │   ├── exec_any_foglamp_command.bash
      │   ├── exec_any_foglamp_command.desc
      │   ├── inject_fogbench_data.bash
      │   ├── read_an_asset_http.bash
      │   ├── README.rst
      │   └── sleep.bash
      └── README.rst

  7 directories, 36 files
  foglamp@vbox-dev:~/FogLAMP/tests/system$


How to Prepare a Test Suite
===========================

In this section we will see how to prepare a new test suite. The objective is to familiarize with the various components, so that you can create your own suite. 


Step 1: the Building Blocks, i.e. the Test Files
------------------------------------------------

The first thing to do is to create some building blocks. These are test files, normally written in bash or Python, that can be reused as many times as you wish in multiple test suites. |br| There are no limitations in the logic you may want to add to each test file, but you should consider these guidelines:

- **Verify the consistency of each file**: the most common error in the test suite is the modification of a test file that is used in many test suites. When you modify a test file, make sure that the file will produce the same results. If the results change, then you must modify all the result files affected by the test file.
- **Document the test file**: it is the most obvious suggestion, but also the one that is often ignored. Try to avoid to create test files that are obscured, with unknown behaviour, because there is a high risk of recreating many times the very same test file simply because you are not aware that there is another test file with the same logic.
- **Do not make test files too generic**: it is ok to pass parameters to test files and make them act as called libraries, but also consider that the more generic the file is, the more it is likely that the execution will produce an unexpected behavior that will cause false failures.
- **Use predefined environment variables**: *foglamp-test* creates some environment variables ready for developer to use. You should use these variables instead of trying to set the same set of variables in a test file.

These are examples of test files:

- *check_foglamp_status*: this script executes the ``foglamp status`` command, but it only provides the first line of the command, i.e. if FogLAMP is running or not.
- *exec_any_foglamp_command*: this is a script used to generically call any command of the *foglamp* utility. 


Pre-defined Variables
~~~~~~~~~~~~~~~~~~~~~

These pre-defined variables are helpful in the test files:

- **FOGLAMP_EXE**: the foglamp script. Based on the *FOGLAMP_ROOT* variable and the presence of the *foglamp* command, the *foglamp-test* utility has already selected the script for you. By using the variable, you will have consistent executions along the whole suite.
- **FOGBENCH_EXE**: the fogbench script. As for *FOGLAMP_EXE*, this variable guarantees the consistency of the execution along the whole suite.
- **SUITE_NAME**: the name of the suite that is currently executed. The variable is also the name of the directory containing the suite files.
- **SUITE_BASEDIR**: the path to the suite directory, i.e. the directory containing all the suite files.
- **TEST_BASEDIR**: the path to the tests directory, i.e. the directory containing the building blocks (the test files) for the suites.
- **RESULT_DIR**: the path to the result directory, which is part of the suite.
- **TEST_NAME**: name of the suite file currently in execution. From the content of this variable, you can find the suite file (suffix .test), the expected file (suffix .expected), the result file (suffix .result) and the temporary files (suffix .temp).


Step 2: the Suite Files
-----------------------

Once you have a set of test files available, you can combine them together in the suite files. There are no limitations to the number of test files added to the suite files, or to the logic added to the suite file to support the execution of the test: theoretically, a developer may completely ignore the test files and add all the logic in the suite file, but in doing so he/she will certainly replicate most of the logic. |br| Here are some guidelines you may want to adopt when you prepare a suite file:

- **Send unnecessary output to /dev/null**: if you do not want to include the output of a command or a test file in the result file, simply add ``> /dev/null 2>&1`` to the line in the suite file.
- **Send intermediate data to a temporary file**: the correct format is to add ``> $RESULT_DIR/$TEST_NAME.temp 2>&1`` to the command that you need to review the output before it will become part of the result file.
- **Use** ``echo -e`` **or** ``expect`` **to manage interactive input**: some scripts require interactive input, and commands like ``echo -e`` can help  in automating the input.

The suite files have access to the same environment variables used by the test files.


Step 3: Putting Everything Together
-----------------------------------

Now you are almost ready to execute your first suite, there is still one important thing missing: the result files. Result files are necessary to provide a comparison between the expected behavior and the actual reasult of a test. The creation of result files is easy, just follow these guidelines:

- **Prepare the test and suite files**: first, you need to select which test files to use and combine them in the suite file.
- **Execute the foglamp-test utility**: it is likely that the utility will stop at the first test with a failure. This happens if the suite file generates an output (a *.result* file), but there are not expected files (a *.expect* file) to compare.
- **Check and approve the result file**: once you are happy with the content of the result file, simply move the file into the *e* (as in "expected") directory, by changing the suffix to *.expected*.
- **Repeat again until the suite is completed**: when you execute the foglamp-test utility again, the first test will pass, but then the utility will stop on the second test. You must repeat this procedure for all the suite files.

One last point: don't worry about the *.result* and *.temp* files left by the utility: *foglamp-test* will remove these files right before the same suite is executed.


Executing a Test Suite
======================

A test suite is executed with the *foglamp-test* utility. You simply move to the *suites* directory in the system test base directory, select the suite you want to execute and run it. The *--list* arguments shows a list of the available suites:

.. code-block:: console

  foglamp@vbox-dev:~/FogLAMP/tests/system/suites$ ./foglamp-test --list
  ##### FogLAMP System Test #####
  Available test suites:
  smoke: Smoke Test suite
  foglamp@vbox-dev:~/FogLAMP/tests/system/suites$


If you want to see details of a suite, select a suite and add the *--list* argument again:

.. code-block:: console

  foglamp@vbox-dev:~/FogLAMP/tests/system/suites$ ./foglamp-test smoke --list
  ##### FogLAMP System Test #####
  Test Suite: smoke
  Smoke Test suite

  Tests in the smoke suite:
  001_prepare:
  >>> bash/exec_any_foglamp_command: Execute the foglamp command with any paremeter.
  >>> bash/check_foglamp_status: Execute the foglamp status command and retrieves the result.
  >>> bash/exec_any_foglamp_command: Execute the foglamp command with any paremeter.
  002_start:
  >>> bash/exec_any_foglamp_command: Execute the foglamp command with any paremeter.
  >>> bash/check_foglamp_status: Execute the foglamp status command and retrieves the result.
  003_inject:
  >>> bash/inject_fogbench_data:
  004_wait_for_flush:
  >>> bash/sleep:
  005_read_from_REST:
  >>> bash/count_assets_http:
  >>> bash/read_an_asset_http:

  foglamp@vbox-dev:~/FogLAMP/tests/system/suites$


Once you have selected the test suite you want to execute, you can run it by simply passing it as a parameter to the *foglamp-test*:

.. code-block:: console

  foglamp@vbox-dev:~/FogLAMP/tests/system/suites$ ./foglamp-test smoke
  ##### FogLAMP System Test #####
  Script Suite: smoke
  Suite DIR:    /home/foglamp/FogLAMP/tests/system/suites/smoke
  Test DIR:     /home/foglamp/FogLAMP/tests/system/tests
  FogLAMP Root: /usr/local/foglamp
  FogLAMP Data:

  Suite Start: 2018-01-31 15:15:06.082467
  [2018-01-31 15:15:06.087680] - 001_prepare - [2018-01-31 15:15:07.067504] (.972 seconds) - PASSED
  [2018-01-31 15:15:07.076041] - 002_start - [2018-01-31 15:15:13.492360] (6.412 seconds) - PASSED
  [2018-01-31 15:15:13.499524] - 003_inject - [2018-01-31 15:15:13.659411] (.155 seconds) - PASSED
  [2018-01-31 15:15:13.666810] - 004_wait_for_flush - [2018-01-31 15:15:23.678761] (10.006 seconds) - PASSED
  [2018-01-31 15:15:23.686204] - 005_read_from_REST - [2018-01-31 15:15:23.732168] (.41 seconds) - PASSED
  Total Execution Time: 17.652 seconds.
  Suite End:   2018-01-31 15:15:23.740412 - COMPLETED
  foglamp@vbox-dev:~/FogLAMP/tests/system/suites$


Let's have a look at the output of this execution:

- The first part of the output shows some generic info, such as the directories and environment variables used by the suite files.
- The second part is about the test execution. It begins with the date and time of when the tests start.
- The following information is related to the individual test files, one for each line. Information are:

  - Starting date and time of the execution of the suite file
  - Name of the suite file
  - Ending date and time of the execution of the suite file
  - Elapsed time in seconds for the execution
  - Result of the execution, i.e. *PASSED* or *FAILED*

- The last part of the output shows the total execution time for the suite and the final date and time.

In the example above, you may see the suite has been completed and all the tests have passed.


Checking a Failed Test
----------------------

This is what you may see if one of the tests if the suite fails:


.. code-block:: console

  foglamp@vbox-dev:~/FogLAMP/tests/system/suites$ ./foglamp-test smoke
  ##### FogLAMP System Test #####
  Script Suite: smoke
  Suite DIR:    /home/foglamp/FogLAMP-997-system_test/tests/system/suites/smoke
  Test DIR:     /home/foglamp/FogLAMP-997-system_test/tests/system/tests
  FogLAMP Root: /usr/local/foglamp
  FogLAMP Data:

  Suite Start: 2018-01-31 16:57:59.332437
  [2018-01-31 16:57:59.337390] - 001_prepare - [2018-01-31 16:58:00.369863] (1.026 seconds) - PASSED
  [2018-01-31 16:58:00.376950] - 002_start - [2018-01-31 16:58:06.792647] (6.410 seconds) - PASSED
  [2018-01-31 16:58:06.800447] - 003_inject - [2018-01-31 16:58:06.960875] (.155 seconds) - PASSED
  [2018-01-31 16:58:06.970094] - 004_wait_for_flush - [2018-01-31 16:58:16.980510] (10.005 seconds) - PASSED
  [2018-01-31 16:58:16.987632] - 005_read_from_REST - [2018-01-31 16:58:17.031112] (.39 seconds) - FAILED - Expect/Result MISMATCH
  Total Execution Time: 17.701 seconds.
  Suite End:   2018-01-31 16:58:17.039578 - INCOMPLETED 
  foglamp@vbox-dev:~/FogLAMP/tests/system/suites$


As you can see, the result of the execution of the suite file *005_read_from_REST* has failed. The utility also gives you an idea of the reason why it fails. Possible reasons are:

- **Expect/Result MISMATCH**: the result of the execution is different from the expected result
- **MISSING Result**: the execution has not generated any result file
- **UNEXPECTED Result**: the execution has generated a result file, but there are no expected results for the execution of this suite file

In the case presented above, the mismatch would be pretty simple to check using the diff utility:


.. code-block:: console

  foglamp@vbox-dev:~/FogLAMP/tests/system/suites$ diff smoke/e/005_read_from_REST.expected smoke/r/005_read_from_REST.result
  4c4
  <     "count": 2
  ---
  >     "count": 1
  foglamp@vbox-dev:~/FogLAMP/tests/system/suites$


So here there is a mismatch between the JSON part of an output expected and the actual result of an executed suite file. Now the developer should figure out what is the issue.


The *smoke* Suite
=================

The *smoke* suite is a simple set of tests that checks if a running version of FogLAMP can perform the basic operations expected by the platform. In its current form, it executes 5 steps:

1. **Test preparation**: stop FogLAMP (if it is currently running) and reset the internal database. Building blocks are:

  - *exec_any_foglamp_command* - passing the ``stop`` argument
  - *check_foglamp_status*
  - *exec_any_foglamp_command* - passing the ``reset`` argument

2. **Test start**: start FogLAMP and make sure that the necessary services are running. Building blocks are:

  - *exec_any_foglamp_command* - passing the ``start`` argument
  - *check_foglamp_status*

3. **Inject a new reading via CoAP using Fogbench**: prepare the injection template and run fogbench. Building blocks are:

  - *inject_fogbench_data* - passing a template prepared by the suite file

4. **Wait for the data to flush**: data is flushed every 5 seconds, so the test waits for 10 seconds before it proceeds to the next step. Building blocks are:

  - *sleep* - passing *10* as a value in seconds

5. **Read data via REST API**: check the count of readings and the content of the reading. Building blocks are:

  - *count_assets_http* - the default (HTTP) connection is used
  - *read_an_asset_http* - passing the key used in the injection step as argument


All steps are replicable and available to Intel and ARM architectures.

