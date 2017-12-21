.. |br| raw:: html

   <br />

**************************************
Building and using FogLAMP on Raspbian
**************************************

FogLAMP requires the use of Python 3.5 in order to support the
asynchronous IO mechanisms used by FogLAMP. Earlier Raspberry Pi Raspbian
distributions support Python 3.4 as the latest version of Python.
In order to build and run FogLAMP on Raspbian the version of Python
must be updated manually if your distribution has an older version.

Check your Python version by running the command
::
    python3 --version
|br|

If your version is less than 3.5 then follow the instructions below to update
your Python version.

Install and update the build tools required for Python to be built
::
    sudo apt-get update
    sudo apt-get install build-essential tk-dev
    sudo apt-get install libncurses5-dev libncursesw5-dev libreadline6-dev
    sudo apt-get install libdb5.3-dev libgdbm-dev libsqlite3-dev libssl-dev
    sudo apt-get install libbz2-dev libexpat1-dev liblzma-dev zlib1g-dev
|br|

Now build and install the new version of Python
::
    wget https://www.python.org/ftp/python/3.5.2/Python-3.5.2.tgz
    tar zxvf Python-3.5.2.tgz
    cd Python-3.5.2
    ./configure
    make
    sudo make install
|br|

Confirm the Python version
::
    python3 --version
    pip3 --version
|br|

These should both return a version number as 3.5, if not then check which
python3 and pip3 you are running and replace these with the newly
built versions. This may be caused by the newly built version being
installed in /usr/local/bin and the existing python3 and pip3 being
in /usr/bin. If this is the case then remove the /usr/bin versions
::
    sudo rm /usr/bin/python3 /usr/bin/pip3
|br|

You may also link tothe new version if you wish
::
    sudo ln -s /usr/bin/python3 /usr/local/bin/python3
    sudo ln -s /usr/bin/pip3 /usr/local/bin/pip3
|br|
Once python3.5 has been installed you may follow the instructions
in the README file to build, install and run FogLAMP on Raspberry
Pi using the Raspbian distribution.
