#!/bin/bash

# Change the cwd to the directory where this script
# is located
SCRIPT=$_
if [[ "$SCRIPT" != "$0" ]]
then
    # See https://unix.stackexchange.com/questions/4650/determining-path-to-sourced-shell-script
    SCRIPT=${BASH_SOURCE[@]}
    if [ "$SCRIPT" == "" ]
    then
        SCRIPT=$_
    fi
else
    SCRIPT=$0
fi

pushd `dirname "$SCRIPT"` > /dev/null
SCRIPTNAME=$(basename "$script")


usage="=== $SCRIPTNAME ===

Activates a Python virtual environment. Installs
Python packages unless -a is provided. Additional
capabilities are available. See the options below.

Usage:
  \"source\" this script for the current shell
  to inherit fogLAMP's Python virtual environment
  located in src/python/env/fogenv. Deactivate the
  environment by running the \"deactivate\" shell
  command.

Options:
  -h, --help      Show this help text
  -a, --activate  Activate the virtual environment and exit
  -c, --clean     Deactivate and clean the virtual environment
  -l, --lint      Run pylint and generate output to pylint-report.txt
  -t, --test      Run tests
  -i, --install   Install the FogLAMP package
  -u, --uninstall Uninstall the  package and remove installed scripts
  -r, --run       Install the FogLAMP package and run foglamp
  -d, --daemon    Install the FogLAMP package and run foglamp-d
  --doc           Generate docs html in docs/_build directory
  --doctest       Run docs/check_sphinx.py"

setup_and_run() {

    IN_VENV=$(python -c 'import sys; print ("1" if hasattr(sys, "real_prefix") else "0")')

    if [ "$option" == "CLEAN" ]
    then
        if [ $IN_VENV -gt 0 ]
        then
            echo "--- Deactivating virtualenv"
            deactivate
        fi
        echo "--- Removing virtualenv directory"
        rm -rf venv
        make clean
        return
    fi

    if [ $IN_VENV -gt 0 ]
    then
        echo "--- virtualenv already active"
    else
        if [ ! -f venv/fogenv/bin/activate ]
        then
            echo "--- Installing virtualenv"
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

            echo "--- Creating the virtualenv using ${python_path}"
            virtualenv "--python=$python_path" venv/fogenv
        fi

        echo "--- Activating the virtualenv at `pwd`/venv/fogenv"
        source venv/fogenv/bin/activate

        IN_VENV=$(python -c 'import sys; print ("1" if hasattr(sys, "real_prefix") else "0")')

        if [ $IN_VENV -lt 1 ]
        then
            echo "*** virtualenv failed. Is virtualenv installed?"
            return
        fi
    fi

    if [ "$option" == "VENV" ]
    then
        return
    fi

    make install-python-requirements

    make copy-config

    if [ "$option" == "LINT" ]
    then
        make lint

    elif [ "$option" == "TEST" ]
    then
        echo "tox is on the job; see tox.ini"
        tox
        # to run only /src/python/tests, use tox -e py35

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
        make doc

    elif [ "$option" == "TEST_DOC" ]
    then
        echo "Running Sphnix docs test"
        tox -e docs

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

           -a|--activate)
             option="VENV"
             ;;

           -l|--lint)
             option="LINT"
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

            -d|--daemon)
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

            --doctest)
              option="TEST_DOC"
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

popd > /dev/null

