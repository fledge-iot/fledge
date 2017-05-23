Requirements:
-------------

* Python 3.5.2
* Ubuntu 16.0.4 or up
* Postgres 9.6.3


Installation:
-------------


``cd src/python``

1. activate virtual env

    ``pip3.5 install virtualenv``

    ``python3.5_path=$( which python3.5 )``

    ``virtualenv --python=$python3.5_path venv/fogenv``

    ``source venv/fogenv/bin/activate``

    make sure, now you see prompt with (fogenv) as prefix


    if using pycharm, make sure to set
    PyCharm > Project Interpreter > Add local ``src/python/venv/fogenv/bin/python``

2. ``pip install -r requirements.txt``


3. **install using setup.py**

   ``venv/fogenv/bin/python setup.py install --record files.txt``

        Installing foglamp script to src/python/venv/fogenv/bin
        Installing foglamp-d script to src/python/venv/fogenv/bin

        Installed src/python/venv/fogenv/lib/python3.6/site-packages/FogLAMP-0.1-py3.6.egg
        Processing dependencies for FogLAMP==0.1

        Finished processing dependencies for FogLAMP==0.1

        writing list of installed files to ``install-info.txt``

       **To uninstall:**

        ``cat install-info.txt | xargs  rm -rf``
        ``rm -rf install-info.txt``


       **To clean:**

        ``python setup.py clean --all``


   **install using pip**

       Check ``./build.sh -h`` in ``src/python/`` directory for quick setup and run.
