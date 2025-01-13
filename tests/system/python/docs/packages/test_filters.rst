Test Filters
~~~~~~~~~~~~

Objective
+++++++++
This test is specifically designed for basic testing of the `fledge-filter-python35` plugin. It incorporates the use of `fledge-south-http-south` for ingesting data into Fledge via Fogbench and `fledge-filter-expression` to verify Fledge's ability to handle multiple filters in a pipeline alongside `fledge-filter-python35`.

This test contains *TestPython35* class, which contains multiple test case functions:

1. **test_filter_python35_with_uploaded_script**: Verifies whether the Python35 filter creates the required assets and datapoints after a script is uploaded in enabled mode. This test also checks the stability of Fledge.
2. **test_filter_python35_with_updated_content**: Verifies whether the reconfiguration of the Python35 filter works correctly by updating the script content and ensuring it creates the required assets and datapoints.
3. **test_filter_python35_disable_enable**: Checks whether Fledge remains stable after disabling and enabling the Python35 filter, and verifies that the required assets and data points are created.
4. **test_filter_python35_expression**: Checks whether Fledge can handle and remain stable when the expression filter is added to the http-south plugin's south service, followed by the Python35 filter. This includes testing the behavior when the south service is disabled and then re-enabled
5. **test_delete_filter_python35**: Verifies whether Fledge can successfully delete the Python35 filter from the http-south plugin's south service.
6. **test_filter_python35_by_enabling_disabling_south**: Checks whether Fledge can disable the south service of fledge-south-http-south plugin, then add the Python35 filter, and re-enable the south service. Ensure that Fledge creates the required assets and datapoints.  
7. **test_delete_south_service**: Verifies the deletion of the `http-south` plugin's south service, which includes the Python35 filter, and checks whether the Python35 script is also removed from the `$FLEDGE_DATA` directory.  


Prerequisite
++++++++++++

Install the prerequisites to run a test:

.. code-block:: console

   $ cd fledge/python
   $ python3 -m pip install -r requirements-test.txt


The minimum required parameters to run,

.. code-block:: console

    --package-build-version=PACKAGE_BUILD_VERSION
                        Package build version for http://archives.fledge-iot.org/
    --wait-time=WAIT_TIME
                        Generic wait time (in seconds) between processes
    --junit-xml=JUNIT_XML
                        Specifies the file path or directory where the JUnit XML test results should be saved.

Execution of Test
+++++++++++++++++

.. code-block:: console

  $ cd fledge/tests/system/python/
  $ python3 -m pytest -s -vv packages/test_filters.py --package-build-version="<PACKAGE_BUILD_VERSION>" --wait-time="<WAIT_TIME>" --junit-xml="<JUNIT_XML>"
