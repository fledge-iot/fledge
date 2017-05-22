#!/bin/bash

# Usage:
   # ./build.sh
   # ./build.sh -h
   # ensure permission: chmod 700 build.sh

usage="$(basename "sh $0") [-h] [-t | --test] [--doc] -- Setup virtual env, install the requirements
where:
    -h  show this help text
    -t, --test run tests
    --doc generate docs html in docs/_build directory"

setup_and_run() {

    echo "--- installing virtualenv ---"
    # shall ignore if already installed
    pip3.5 install virtualenv

    # which python3.5
    python3.5_path=$( which python3.5 )

    echo "--- setting the virtualenv using python3.5 path; should be 3.5.2 found $python3.5_path ---"

    virtualenv --python=$python3.5_path venv/fogenv
    source venv/fogenv/bin/activate

    # make sure you see prompt now with (fogenv) as prefix

    echo "--- installing requirements which were frozen using [pip freeze > requirements.txt]---"
    pip install -r requirements.txt

    if [ "$option" == "TEST" ]
    then
        echo "run tests? will add tox.ini to run via tox"
        echo "until then, checking db config"
        python tests/db_config.py

    elif [ "$option" == "BUILD_DOC" ]
    then
        echo "Running make html in docs"
        cd ../../docs
        make html
    fi

    # echo "--- deactivating the virtualenv ---"
    # deactivate

    # echo "--- removing virtualenv directory ---"
    # rm -rf venv/fogenv/
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