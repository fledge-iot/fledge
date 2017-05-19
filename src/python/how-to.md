## python3.6






#### Running python foglamp package

`cd src/python`

1. setup and activate virtual env

    > if using pycharm, make sure to set
    
    > PyCharm > Project Interpreter > Add local `src/python/venv/fogenv/bin/python`

2. `pip install -r requirements.txt`


3. `python setup.py develop`

> Adding FogLAMP 0.1 to easy-install.pth file

> Installing foglamp script to /usr/local/bin

> Installing foglamp-d script to /usr/local/bin

#### To clean:

`python setup.py clean --all`

> you may want: `/usr/local/bin`  $ `rm -rf foglamp foglamp-d`