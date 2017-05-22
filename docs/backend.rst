Requirements:
-------------

* Python 3.5.2
* Ubuntu 16.0.4 or up
* Postgres 9.6.3


Installation:
-------------

Check ``build.sh`` in ``src/python/`` directory for quick setup and run.

``cd src/python``

1. setup and activate virtual env

    ``pip3.5 install virtualenv``

    ``python3.5_path=$( which python3.5 )``

    ``virtualenv --python=$python3.5_path venv/fogenv``

    ``source venv/fogenv/bin/activate``

    make sure, now you see prompt with (fogenv) as prefix


    if using pycharm, make sure to set
    PyCharm > Project Interpreter > Add local ``src/python/venv/fogenv/bin/python``

2. ``pip install -r requirements.txt``


3. ``python setup.py develop --user``

   Adding FogLAMP 0.1 to easy-install.pth file

   Installing foglamp script to ``~/.local/bin``

   Installing foglamp-d script to ``~/.local/bin``

   **To clean:**

   ``python setup.py clean --all``

   You may want: ``~/.local/bin$ rm -rf foglamp foglamp-d``