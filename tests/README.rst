.. FogLAMP test scripts describes how to FogLAMP scripted tests are organised and how to write the scripted tests

.. |br| raw:: html

   <br />

.. Links

.. Links in new tabs

.. |pytest docs| raw:: html

   <a href="https://docs.pytest.org/en/latest/contents.html" target="_blank">pytest</a>

.. |pytest decorators| raw:: html

   <a href="https://docs.pytest.org/en/latest/mark.html" target="_blank">pytest</a>

.. _Unit: unit\\README.rst
.. _Integration: integration\\README.rst
.. _System: system\\README.rst
.. _here: ..\\README.rst

.. =============================================

********************
FogLAMP Test Scripts
********************

FogLAMP scripted tests are classified into three categories:

- `Unit`_ - Tests that checks the expected output of a code block.
- `Integration`_ - Tests that checks the integration of different FogLAMP units that work as a single component.
- `System`_ - Tests that checks the end to end flows in FogLAMP


Running FogLAMP scripted tests
==============================

Test Prerequisites
------------------

Follow the instructions mentioned `here`_  to install and run FogLAMP on your machine.
You can test FogLAMP from your development environment or after installing FogLAMP.

To install the dependencies required to run python tests, run the following command from FOGLAMP_ROOT
::
   pip3 install -r python/requirements-test.txt --user


Test Execution
--------------

Python Tests
++++++++++++

FogLAMP uses pytest as the test runner for testing python based code. For more information on pytest please refer
|pytest docs|
To execute a single test, navigate to the directory where your test code is placed and execute the command
``pytest test_filename.py`` where test_filename.py is the name of the file which contains your tests.

pytest also supports running of a complete test suite. To execute the complete test suite, navigate to the directory
which contains the tests and run the command ``pytest`` . This will execute all the python tests in the given directory
and sub-directories.

**NOTE:** *FogLAMP integration tests can be executed individually and not in suite because of an open issue.
Further information to run the different categories of tests can be found in their respective documentation*

FogLAMP also use |pytest decorators| heavily. For example pytest allure decorators like:
::
   @pytest.allure.feature("unit")
   @pytest.allure.story("south")

feature can be anything from unit, integration and system and story is FogLAMP component/sub-component.
These decorators are used in generating allure test reports on CI systems.


C Tests
+++++++

TO-DO

Test addition
-------------

If you want to contribute towards adding a new tests in FogLAMP, make sure you follow some rules:

- Test file name should begin with the word ``test_`` to enable pytest auto test discovery.
- Make sure you are placing your test file in the correct test directory. For example, if you are writing a unit test, it should be located under ``$FOGLAMP_ROOT/tests/unit/python/foglamp/<component>`` where component is the name of the component for which you are writing the unit tests. For more information of type of test, refer to the test categories.
