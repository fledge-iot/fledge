Build Tools
===========

Coverage Report
---------------

 Test coverage report helps you to analyse the code covered by your unit tests.

 Foglamp uses `pytest-cov <http://pytest-cov.readthedocs.io/en/latest/readme.html>`_ (pytest plugin for coverage reporting) to check the code coverage.

How to run Test Coverage (through make)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- ``make py-test`` : This installs required dependencies, run python tests and generates coverage report in html format.
- ``make cov-report`` : Opens coverage report htmlcov/index.php in your default browser

How to read coverage report
^^^^^^^^^^^^^^^^^^^^^^^^^^^

- index.html page displays the test coverage of all the files

  .. image:: images/coverage_report.png

- To see the details of file, click on the file hyperlink, this will navigate you to the file details which shows the code covered (in green) and code not covered (in red) by the unit tests

  .. image:: images/coverage_report_file_details.png

How to modify configuration of coverage
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

 Default configuration of coverage report is stored in the file ``.coveragerc`` . If you want to include tests in your code coverage, remove ``/*/tests/*`` from the omit option.



Test Report
-----------

 Foglamp uses `Allure <http://allure.qatools.ru/>`_ to visualise the test reports.

Prerequisite
^^^^^^^^^^^^

 Install allure on your local machine. Use instructions listed `here <http://wiki.qatools.ru/display/AL/Allure+Commandline>`_

How to generate Allure Report (through make)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- ``make py-test`` : This installs required dependencies, run python tests.
- ``make test-report``: This generates allure reports, Starting web server for report directory <allure-report> and displays the report in your browser.
- To stop the web server and exit, press ``Ctrl+C`` from your terminal.

