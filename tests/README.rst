.. Fledge test scripts describes how to Fledge scripted tests are organised and how to write the scripted tests

.. |br| raw:: html

   <br />

.. Links

.. Links in new tabs

.. |pytest docs| raw:: html

   <a href="https://docs.pytest.org/en/latest/contents.html" target="_blank">pytest</a>

.. |pytest decorators| raw:: html

   <a href="https://docs.pytest.org/en/latest/mark.html" target="_blank">pytest</a>

.. _Unit: unit\\python\\
.. _System: system\\
.. _here: ..\\README.rst

.. =============================================

********************
Fledge Test Scripts
********************

Fledge scripted tests are classified into two categories:

- `Unit`_ - Tests that checks the expected output of a code block.
- `System`_ - Tests that checks the end to end and integration flows in Fledge


Running Fledge scripted tests
==============================

Test Prerequisites
------------------

Follow the instructions mentioned `here`_  to install and run Fledge on your machine.
You can test Fledge from your development environment or after installing Fledge.

To install the dependencies required to run python tests, run the following command from FLEDGE_ROOT
::
   python3 -m pip install -r python/requirements-test.txt --user
   sudo apt install jq libxslt-dev


Test Execution
--------------

Python Tests
++++++++++++

Fledge uses pytest as the test runner for testing python based code. For more information on pytest please refer
|pytest docs|
Running the python tests:

- ``pytest`` - This will execute all the python test files in the given directory and sub-directories.
- ``pytest test_filename.py`` - This will execute all tests in the file named test_filename.py
- ``pytest test_filename.py::TestClass`` -  This will execute all test methods in a single class TestClass in file test_filename.py
- ``pytest test_filename.py::TestClass::test_case`` - This will execute test method test_case in class TestClass in file test_filename.py

**NOTE:** *Information to run the different categories of tests can be found in their respective documentation*

Fledge also use |pytest decorators| heavily. For example pytest allure decorators like:
::
   @pytest.allure.feature("unit")
   @pytest.allure.story("south")

feature can be anything from unit or system and story is Fledge component/sub-component.
These decorators are used in generating allure test reports on CI systems.


C Tests
+++++++

TO-DO

Test addition
-------------

If you want to contribute towards adding a new tests in Fledge, make sure you follow some rules:

- Test file name should begin with the word ``test_`` to enable pytest auto test discovery.
- Make sure you are placing your test file in the correct test directory. For example, if you are writing a unit test, it should be located under ``$FLEDGE_ROOT/tests/unit/python/fledge/<component>`` where component is the name of the component for which you are writing the unit tests. For more information of type of test, refer to the test categories.
