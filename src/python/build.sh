#!/bin/bash

called=$_
if [[ "$called" != "$0" ]] 
then 
    script=$BASH_SOURCE
else 
    script=$0
fi

usage="$(basename $script)

This script sets up a virtual Python environment via virtualenv.
It also installs Python packages unless -v is provided.
Additional activities are available. See below.

Usage:
  Invoke this script via "source" in order for the shell
  to inherit fogLAMP's Python virtual environment located in
  src/python/env/fogenv

Options:
  -h, --help       Show this help text
  -v, --virtualenv Only set up virtual environment
  -c, --clean      Deactivate and clean the virtual environment
  -t, --test       Runs tests
  -i, --install    Installs the FogLAMP package
  -r, --run        Installs the FogLAMP package and run foglamp
  --rd, --daemon   Installs the FogLAMP package and run foglamp-d
  -u, --uninstall  Uninstalls the  package and remove installed scripts
  --doc            Generate docs html in docs/_build directory"

# Change the cwd to the directory where this script
# is located
change_dir() {
    pushd `dirname "$script"` > /dev/null
    sdir=`pwd`
    popd > /dev/null
    echo Changing directory to $sdir
    pushd "$sdir"
}

setup_and_run() {

    IN_VENV=$(python -c 'import sys; print ("1" if hasattr(sys, "real_prefix") else "0")')

    if [ "$option" == "CLEAN" ]
     then
        if [ $IN_VENV -gt 0 ]
        then
            echo "--- deactivating virtualenv ---"
            deactivate
        fi
        echo "--- removing virtualenv directory ---"
        rm -rf venv
        return
    fi

    if [ $IN_VENV -gt 0 ]
    then
        echo "*** virtualenv is already running; Run with -c | --clean to cleanup"
	return
    fi

    echo "--- installing virtualenv ---"
    # shall ignore if already installed
    pip3 install virtualenv

    if [ $? -gt 0 ]
    then
        echo "*** pip3 failed installing virtualenv"
	return
    fi

    # which python3
    python_path=$( which python3.5 )

    if [ $? -gt 0 ]
    then
        echo "*** python3.5 is not found"
	return
    fi

    echo "--- setting the virtualenv using ${python_path} ---"

    virtualenv --python=$python_path venv/fogenv

    if [ $? -gt 0 ]
    then
        echo "*** virtualenv failed. Is virtualenv installed?"
	return
    fi

    source venv/fogenv/bin/activate

    if [ "$option" == "VENV" ]
    then
	return
    fi

    echo "--- installing requirements which were frozen using [pip freeze > requirements.txt]---"
    pip install -r requirements.txt

    if [ "$option" == "TEST" ]
    then
        echo "run tests? will add tox.ini to run via tox"
        echo "until then, checking db config"

        pip install -e .
        python tests/db_config.py
        pip uninstall FogLAMP <<< y

    elif [ "$option" == "INSTALL" ]
    then
        pip install -e .

    elif [ "$option" == "RUN" ]
    then
        pip install -e .
        foglamp

    elif [ "$option" == "RUN_DAEMON" ]
    then
        pip install -e .
        foglamp-d

    elif [ "$option" == "BUILD_DOC" ]
    then
        echo "Running make html in docs"
        cd ../../docs/
        make html
        cd ../src/python/

    elif [ "$option" == "UNINSTALL" ]
    then
        echo "This will remove the package"
        pip uninstall FogLAMP <<< y

    fi
}

option=''
change_dir

if [ $# -gt 0 ]
  then
     for i in "$@"
     do
         case $i in

           -v|--virtualenv)
             option="VENV"
             ;;

           -t|--test)
             option="TEST"
             ;;

           -i|--install)
             option="INSTALL"
             ;;

            -r|--run)
             option="RUN"
             ;;

            -rd|--daemon)
             option="RUN_DAEMON"
             ;;

            -u|--uninstall)
             option="UNINSTALL"
             ;;

            -c|--clean)
             option="CLEAN"
             ;;

            --doc)
             option="BUILD_DOC"
             ;;

            *)
             echo "${usage}" # anything including -h :]
             break
             ;;
         esac
         setup_and_run
     done
  else
     setup_and_run
fi

popd