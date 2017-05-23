#!/bin/bash

set -e

# Usage:
   # ./build.sh
   # ./build.sh -h
   # ensure permission: chmod 700 build.sh

usage="$(basename "sh $0") [-h] [-t | --test] [--doc] -- Setup virtual env, install the requirements
where:
    -h  show this help text
    -t, --test runs tests
    -i, --install installs the FogLAMP package
    -r, --run installs the FogLAMP package and run foglamp
    --rd, --daemon installs the FogLAMP package and run foglamp-d
    -u, --uninstall uninstalls the  package and remove installed scripts
    --doc generate docs html in docs/_build directory"

setup_and_run() {

    if [ "$option" == "CLEAN" ]
     then
        echo "--- removing virtualenv directory ---"
        rm -rf venv
        return
    fi

    echo "--- installing virtualenv ---"
    # shall ignore if already installed
    pip3 install virtualenv

    # which python3
    python_path=$( which python3 )

    echo "--- setting the virtualenv using python_path; should be 3.5.2 found ${python_path} ---"

    virtualenv --python=$python_path venv/fogenv
    source venv/fogenv/bin/activate


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

if [ $# -gt 0 ]
  then
     for i in "$@"
     do
         case $i in

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