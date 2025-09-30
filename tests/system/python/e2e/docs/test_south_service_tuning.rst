Test South Service Tuning
~~~~~~~~~~~~~~~~~~~~~~~~~

Objective
+++++++++
This test is designed to check the effect of south service tuning parameters on the performance of Fledge. By default, it uses the `fledge-south-sinusoid` plugin to ingest data into Fledge, Other plugin can also be used by changing the command line parameter `--south-plugin`. The test measures ingested number of readings with different tuning parameters and compares the results.

This test contains *TestSouthServiceTuning* class, which contains multiple test case functions:

1. **test_south_service_tuning_buffer_threshold**: 
2. **test_south_service_comprehensive_tuning**: 
3. **test_buffer_threshold_impact_on_send_frequency**: 
4. **test_max_send_latency_impact**: 


Prerequisite
++++++++++++

1. Fledge must be installed by `make` command
2. The FLEDGE_ROOT environment variable should be exported to the directory where Fledge is installed.
3. Install the prerequisites to run a test:

.. code-block:: console

   $ cd fledge/python
   $ python3 -m pip install -r requirements-test.txt --user



Execution of Test
+++++++++++++++++

.. code-block:: console

  $ export FLEDGE_ROOT=<path_to_fledge_installation>
  $ export PYTHONPATH=$FLEDGE_ROOT/python
  $ cd fledge/tests/system/python/
  $ python3 -m pytest -s -vv e2e/test_south_service_tuning.py --south-plugin sinusoid --plugin-language python
