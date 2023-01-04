.. FLedge system tests involving iprpc module.

.. |br| raw:: html

   <br />

.. Links

.. Links in new tabs

.. |pytest docs| raw:: html

   <a href="https://docs.pytest.org/en/latest/contents.html" target="_blank">pytest</a>

.. |pytest decorators| raw:: html

   <a href="https://docs.pytest.org/en/latest/mark.html" target="_blank">pytest</a>

.. _iprpc: ..\\..\\..\\..\\python\\fledge\\common\\iprpc.py
.. _numpy_south: ..\\plugins\\dummy\\iprpc\\south\\numpy_south\\numpy_south.py
.. _numpy_filter: ..\\plugins\\dummy\\iprpc\\filter\\numpy_filter\\numpy_filter.py
.. _numpy_iprpc_filter: ..\\plugins\\dummy\\iprpc\\filter\\numpy_iprpc_filter\\numpy_iprpc_filter.py

.. =============================================

*************************
Fledge IPRPC System Tests
*************************

Fledge system tests involving the `iprpc`_ module are given below:

1.  A test that uses numpy module in both south plugin and filter plugin. But fails to use it simultaneously because numpy cannot be re initialized in sub interpreter when already initialized in parent interpreter.
2.  The same plugins are used except this time the filter plugin uses the iprpc facility to perform an operation specific to numpy.

There are three dummy plugins used in the tests.

1. `numpy_south`_ - A plugin that ingests random values in Fledge using numpy 's random function.
2. `numpy_filter`_ - A plugin which calculates root mean square on the values it gets from south service and creates an extra asset for rms_values. However it does not uses iprpc facility.
3. `numpy_iprpc_filter`_ - Similar to numpy_filter but uses iprpc facility.

**NOTE**

The south service may or may not use iprpc facility. However it is mandatory to use iprpc facility when
both south and filter plugins use modules like numpy.

Scenarios
=========

While testing following settings can be present.

.. list-table:: Results
   :widths: 25 25 50
   :header-rows: 1

   * - South Plugin
     - Filter Plugin
     - Expected Result
   * - The plugin uses numpy module
     - The plugin uses numpy without iprpc module
     - South service crashes
   * - The plugin does not use numpy module
     - The plugin uses numpy without iprpc module
     - Service does not crash however Runtime error wrt to numpy module is observed.
   * - The plugin uses numpy module
     - The plugin does not use numpy.
     - Working Fine.
   * - The plugin uses numpy module.
     - The plugin uses numpy with iprpc module.
     - Working Fine.


Running Fledge System tests involving iprpc
===========================================

Test Prerequisites
------------------

To install the dependencies required to run python tests, run the following two commands from FLEDGE_ROOT
::

    cd $FLEDGE_ROOT/tests/system/python/iprpc
    python3 -m pip install -r requirements-iprpc-test.txt --user


Test Execution
--------------


After installing the Prerequisites
::

    python3 -m pytest -s -v test_iprpc.py --fledge-url localhost:8081
