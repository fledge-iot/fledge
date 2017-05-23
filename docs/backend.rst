Requirements:
-------------

* Python 3.5.2
* Ubuntu 16.0.4 or up
* Postgres 9.6.3


Installation:
-------------


``cd src/python``

1. activate virtual env

    ``pip3 install virtualenv``

    ``python3.5_path=$( which python3 )``

    ``virtualenv --python=$python3.5_path venv/fogenv``

    ``source venv/fogenv/bin/activate``

    Make sure, now you see prompt with (fogenv) as prefix


    if using pycharm, make sure to set

    PyCharm > Project Interpreter > Add local ``src/python/venv/fogenv/bin/python``

2. ``pip install -r requirements.txt``


3. **installation**

   3.1 **using setup.py**

       ``python setup.py install --user --prefix= --record install-info.txt``

            Installing foglamp script to src/python/venv/fogenv/bin

            Installing foglamp-d script to src/python/venv/fogenv/bin

            Installed src/python/venv/fogenv/lib/python3.5/site-packages/FogLAMP-0.1-py3.5.egg

            Processing dependencies for FogLAMP==0.1

            Finished processing dependencies for FogLAMP==0.1

            writing list of installed files to ``install-info.txt``

       **To uninstall:**

            ``cat install-info.txt | xargs  rm -rf``

            ``rm -rf install-info.txt``


       **To clean:**

            ``python setup.py clean --all``

       [if not in virtual env, it will install in ~/.local/bin for ubuntu] Actually check: ``install-info.txt``


   3.2 **using pip**

       Check ``./build.sh -h`` in ``src/python/`` directory for quick setup and run.
