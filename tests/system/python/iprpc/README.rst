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
.. _numpy_iprpc_south: ..\\plugins\\dummy\\iprpc\\south\\numpy_iprpc_south\\numpy_iprpc_south.py
.. _numpy_filter: ..\\plugins\\dummy\\iprpc\\filter\\numpy_filter\\numpy_filter.py
.. _numpy_iprpc_filter: ..\\plugins\\dummy\\iprpc\\filter\\numpy_iprpc_filter\\numpy_iprpc_filter.py

.. =============================================

*************************
Fledge IPRPC System Tests
*************************

Fledge system tests involving the `iprpc`_ module are given below:

1.  A test that uses numpy module in both south plugin and filter plugin. But fails to use it simultaneously because numpy cannot be re initialized in sub interpreter when already initialized in parent interpreter.
2.  The same plugins are used except this time the filter plugin uses the iprpc facility to perform an operation specific to numpy.

There are four dummy plugins used in the tests.


1. `numpy_south`_ - A plugin that ingests random values in Fledge similar to sinusoid plugin but uses numpy random function.
2. `numpy_iprpc_south`_ - A plugin similar to numpy_south and does not use iprpc facility to perform numpy operations.
3. `numpy_filter`_ - A plugin which calculates root mean square on the values it gets from south service and creates an extra asset for rms_values. However it does not uses iprpc facility.
4. `numpy_iprpc_filter`_ - Similar to numpy_filter but uses iprpc facility.

**NOTE**

The south service may or may not use iprpc facility. However it is mandatory to iprpc facility when :

1. Both south and filter plugins use modules like numpy.
2. The filter plugin uses modules like numpy and south plugin is just any other plugin like sinusoid.


Running Fledge System tests involving iprpc
===========================================

Test Prerequisites
------------------

To install the dependencies required to run python tests, run the following two commands from FLEDGE_ROOT
::

    cd $FLEDGE_ROOT/tests/system/python/iprpc
    pip3 install -r requirements-iprpc-test.txt --user


Test Execution
--------------


After installing the Prerequisites
::

    python3 -m pytest -s -v test_iprpc.py --fledge-url localhost:8081
