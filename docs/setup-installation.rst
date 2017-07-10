Setup and Installation
======================

Requirements
------------

* Python 3.5.2
* Ubuntu 16.0.4 and above
* Postgres 9.6.3


Installation
------------

Check ``./build.sh -h`` in ``src/python/`` directory for quick setup and run.

- To work with the project in virtual environment, use `build.sh`
   - to activate virtual environment use ``source build.sh -a``
   - then, you can use either make targets or build.sh command options

- To work **without virtual environment**, use `Makefile`
   - ``make develop`` will install development dependencies and install the foglamp in editable mode


Note:
^^^^^

Configure python interpreter for PyCharm:

- with virtual env: PyCharm > Project Interpreter > Add local ``src/python/venv/<host machine>/bin/python``
- without virtual env: PyCharm > Project Interpreter > ``Select appropriate python (here, 3.5) path``

``./build.sh`` essentially use `src/python/Makefile` targets
