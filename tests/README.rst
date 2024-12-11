.. Fledge test scripts describes how to Fledge scripted tests are organised and how to write the scripted tests

.. |br| raw:: html

   <br />

.. Links

.. Links in new tabs

.. |pytest docs| raw:: html

   <a href="https://docs.pytest.org/en/latest/contents.html" target="_blank">pytest</a>

.. |pytest decorators| raw:: html

   <a href="https://docs.pytest.org/en/latest/mark.html" target="_blank">pytest</a>

.. |pytest-cov docs| raw:: html

   <a href="https://pytest-cov.readthedocs.io/en/v2.9.0/" target="_blank">pytest-cov</a>

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


C Tests
+++++++

TO-DO

Test addition
-------------

If you want to contribute towards adding a new tests in Fledge, make sure you follow some rules:

- Test file name should begin with the word ``test_`` to enable pytest auto test discovery.
- Make sure you are placing your test file in the correct test directory. For example, if you are writing a unit test, it should be located under ``$FLEDGE_ROOT/tests/unit/python/fledge/<component>`` where component is the name of the component for which you are writing the unit tests. For more information of type of test, refer to the test categories.

Code Coverage
-------------

Python Tests
++++++++++++

Fledge uses pytest-cov Framework of pytest as the code coverage measuring tool for python tests, For more information on pytest-cov please refer to |pytest-cov docs|.

To install pytest-cov Framework along with pytest Framework use the following command:
::
   python3 -m pip install pytest==3.6.4 pytest-cov==2.9.0

Running the python tests:

- ``pytest --cov=. --cov-report xml:xml_filepath --cov-report html:html_directorypath`` - This will execute all the python test files in the given directory and sub-directories and generate the code coverage report in XML as well as the HTML format at the specified path in the command.
- ``pytest test_filename.py --cov=. --cov-report xml:xml_filepath --cov-report html:html_directorypath`` - This will execute all tests in the file named test_filename.py and generate the code coverage report in XML as well as the HTML format at the specified path in the command.
- ``pytest test_filename.py::TestClass --cov=. --cov-report xml:xml_filepath --cov-report html:html_directorypath`` -  This will execute all test methods in a single class TestClass in file test_filename.py and generate the code coverage report in XML as well as the HTML format at the specified path in the command.
- ``pytest test_filename.py::TestClass::test_case --cov=. --cov-report xml:xml_filepath --cov-report html:html_directorypath`` - This will execute test method test_case in class TestClass in file test_filename.py and generate the code coverage report in XML as well as the HTML format at the specified path in the command.
- ``pytest -s -vv tests/unit/python/fledge/ --cov=. --cov-report=html --cov-config $FLEDGE_ROOT/tests/unit/python/.coveragerc`` - This will execute all the python tests and generate the code coverage report in the HTML format on the basis of settings in the configuration file.


C Tests
+++++++

TODO: FOGL-8497 Add documentation of Code Coverage of C Based tests
